"""Post-link snapshot for the Windows/Ninja build; runtime never reads build sources."""

import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def command_args(command):
    if os.name != "nt":
        raise RuntimeError("Build manifest currently requires Windows/Ninja")
    count = ctypes.c_int()
    split = ctypes.windll.shell32.CommandLineToArgvW
    split.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_int)]
    split.restype = ctypes.POINTER(ctypes.c_wchar_p)
    ptr = split(command, ctypes.byref(count))
    if not ptr:
        raise ValueError("Cannot parse compiler command")
    try:
        return [ptr[i] for i in range(count.value)]
    finally:
        free = ctypes.windll.kernel32.LocalFree
        free.argtypes = [ctypes.c_void_p]
        free(ptr)


def dependency_map(text, build):
    result = {}
    current = None
    for line in text.splitlines():
        match = re.fullmatch(r"(.+): #deps \d+.*\((VALID|STALE)\)", line)
        if match:
            current = (build / match[1]).resolve()
            result[current] = [] if match[2] == "VALID" else None
        elif line.startswith("    ") and current is not None and result[current] is not None:
            result[current].append((build / line.strip()).resolve())
    return result


def label(path, root):
    path = Path(path).resolve()
    if path.is_relative_to(root):
        return path.relative_to(root).as_posix()
    for i, part in enumerate(path.parts):
        if part.startswith(("STM32Cube_FW_", "xpack-arm-none-eabi-")):
            return "/".join(path.parts[i:])
    # Unknown installations retain only a basename; file hash still identifies content.
    return "external/" + path.name


def version_macros(text):
    return {name: int(value, 0) for name, value in re.findall(
        r"^\s*#define\s+(__(?:STM32\w*|CM\w*)_VERSION_(?:MAIN|SUB1|SUB2|SUB|RC))"
        r"[ \t]+\(?[ \t]*(0x[0-9A-Fa-f]+|[0-9]+)[uUlL]*[ \t]*\)?[ \t]*(?:/\*[^\n]*|//[^\n]*)?$", text.replace("\r\n", "\n"), re.M)}


def selected_flags(args):
    # Exact command hash is also retained; this human-readable list deliberately omits paths.
    return [arg for arg in args if arg.startswith(("-D", "-U", "-O", "-g", "-m", "-f", "-std=", "--specs="))
            and re.fullmatch(r"[-A-Za-z0-9_+=.,]+", arg)]


def snapshot(root, build, elf, profile, ninja, target=None, extra_inputs=()):
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    def run(args):
        return subprocess.check_output(args, cwd=build, text=True, timeout=20, creationflags=flags)
    deps = dependency_map(run([ninja, "-t", "deps"]), build)
    database = json.loads((build / "compile_commands.json").read_text(encoding="utf-8"))
    units, compilers, files = [], {}, set()
    for row in database:
        obj = (Path(row["directory"]) / row["output"]).resolve()
        # This MVP attaches to the single firmware target, not arbitrary host/helper targets.
        if not obj.is_relative_to(build / "CMakeFiles" / ((target or elf.stem) + ".dir")):
            continue
        dependencies = deps.get(obj)
        source = Path(row["file"]).resolve()
        # Plain assembler has no depfile in this toolchain. Includes need explicit support.
        if (obj not in deps or deps[obj] == []) and source.suffix == ".s":
            if re.search(r"(?m)^\s*(?:\.include|\.incbin|#\s*include)\b", source.read_text()):
                raise ValueError("Assembler includes require dependency tracking")
            dependencies = [source]
        if not dependencies:
            raise ValueError("Missing/stale Ninja dependencies; rebuild firmware: " + obj.name)
        if any(p.stat().st_mtime_ns > obj.stat().st_mtime_ns for p in dependencies):
            raise ValueError("Dependency changed after compilation; rebuild firmware: " + obj.name)
        args = command_args(row["command"])
        compiler = Path(args[0]).resolve()
        if compiler not in compilers:
            compilers[compiler] = dict(name=compiler.name, sha256=digest(compiler),
                                      version=run([str(compiler), "-dumpfullversion"]).strip())
        files.update(dependencies)
        units.append(dict(source=label(row["file"], root), object_sha256=digest(obj),
                          compiler=compiler.name, flags=selected_flags(args),
                          command_sha256=hashlib.sha256(row["command"].encode()).hexdigest()))
    if not units:
        raise ValueError("No firmware objects found in compile_commands.json")
    files.add(profile)
    files.update(Path(p).resolve() for p in extra_inputs)
    if (root / "stm32_config.yml").exists():
        files.add(root / "stm32_config.yml")
    files.update(profile.parent.glob("*.ioc"))
    files.update(profile.parent.glob("*_FLASH.ld"))
    inputs, versions, cubes = [], [], set()
    for path in sorted(files):
        data = path.read_bytes()
        name = label(path, root)
        sha = hashlib.sha256(data).hexdigest()
        inputs.append(dict(file=name, sha256=sha))
        macros = version_macros(data.decode("utf-8", errors="replace"))
        if macros:
            versions.append(dict(file=name, sha256=sha, macros=macros))
        cubes.update(part for part in path.parts if part.startswith("STM32Cube_FW_"))
    return dict(schema=1, evidence="post-link Ninja dependency snapshot",
                elf_sha256=digest(elf), profile_sha256=digest(profile),
                compilers=list(compilers.values()), units=units, inputs=inputs,
                cube_packages=sorted(cubes), library_versions=versions,
                limitations=["No concurrent source edits during build; timestamps must be reliable",
                             "Compiler installation must remain unchanged between compilation and snapshot",
                             "Plain assembler supports no includes; single firmware target only",
                             "Version macros are source declarations, not HAL API compatibility checks",
                             "Linker flags and prebuilt runtime library contents are not captured"])


def load_verified(path, elf_hash, profile):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1:
        raise ValueError("Unsupported build manifest schema")
    if data.get("elf_sha256") != elf_hash:
        raise ValueError("Build manifest does not match ELF; rebuild the selected firmware")
    if data.get("profile_sha256") != digest(profile):
        raise ValueError("Build manifest does not match target profile; rebuild firmware")
    for key in ("compilers", "units", "inputs", "library_versions", "cube_packages"):
        if not isinstance(data.get(key), list) or not data[key]:
            raise ValueError("Incomplete build manifest: " + key)
    return data


def main():
    parser = argparse.ArgumentParser()
    for key in ("root", "build", "elf", "profile", "out"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--ninja", required=True)
    parser.add_argument("--target")
    parser.add_argument("--input", action="append", type=Path, default=[])
    args = parser.parse_args()
    root, build, output = args.root.resolve(), args.build.resolve(), args.out.resolve()
    if not build.is_relative_to(root) or not output.is_relative_to(build):
        raise ValueError("Manifest outputs must stay inside repository build directory")
    output.unlink(missing_ok=True)
    result = snapshot(root, build, args.elf.resolve(), args.profile.resolve(), args.ninja, args.target, args.input)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)


if __name__ == "__main__":
    main()
