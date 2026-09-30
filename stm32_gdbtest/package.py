"""Prepared run packages (ТЗ 5.19): prepare where the toolchain is, run where the stand is.

A package is one zip file with the firmware ELF, its build manifest, the MCU profile
with its tests directory, optional helper files and ddtt-package.json, which lists
the scenarios and the SHA-256 of every file. The stand side verifies every hash
before a run and uses only its own GDB and stand; nothing is rebuilt there.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import zipfile

from stm32_gdbtest import __version__
from stm32_gdbtest.collect import collect
from stm32_gdbtest.toolchain import find_gdb

SCHEMA = 1
MANIFEST = "ddtt-package.json"
RESERVED = {"firmware.elf", "build-manifest.json", "profile", "runs", MANIFEST}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _files(session, include):
    root = Path(session["root"]).resolve()
    profile = Path(session["profile"]).resolve()
    tests_dir = Path(session["tests"]).resolve()
    # Scenarios live in <tests-root>/board; the whole tests root (requirements, contracts)
    # becomes profile/tests, whether or not target.toml sits next to it (ТЗ 5.19.1).
    tests_root = tests_dir.parent
    files = {"firmware.elf": Path(session["elf"]).resolve(), "profile/target.toml": profile}
    if session.get("build_manifest"):
        files["build-manifest.json"] = Path(session["build_manifest"]).resolve()
    for path in sorted(tests_root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            files["profile/tests/" + path.relative_to(tests_root).as_posix()] = path
    for item in include:
        source = (root / item).resolve()
        if not source.is_relative_to(root) or source == root:
            raise ValueError(f"Included path must be inside the project root: {item}")
        paths = sorted(p for p in source.rglob("*") if p.is_file()) if source.is_dir() else [source]
        for path in paths:
            name = path.relative_to(root).as_posix()
            if name.split("/")[0] in RESERVED or "__pycache__" in path.parts:
                continue
            files[name] = path
    return files, "profile/tests/" + tests_dir.name


def pack(session, output, test_ids=None, include=(), prepare=None):
    """Write the package; `prepare(test)` runs the preflight of each packaged scenario."""
    tests = collect(session["tests"])
    if test_ids:
        unknown = sorted(set(test_ids) - {t["id"] for t in tests})
        if unknown:
            raise ValueError("Unknown scenario: " + ", ".join(unknown))
        tests = [t for t in tests if t["id"] in test_ids]
    prepared = {}
    if prepare:
        for test in tests:
            prepared[test["id"]] = prepare(test)
        failed = sorted(k for k, v in prepared.items() if v != "PASS")
        if failed:
            raise RuntimeError("Preparation failed, package not written: " + ", ".join(failed))
    files, tests_dir = _files(session, include)
    manifest = dict(schema=SCHEMA, format="ddtt-package", tool="stm32-gdbtest", tool_version=__version__,
                    created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    elf_sha256=_sha(files["firmware.elf"]), tests_dir=tests_dir,
                    tests=[dict(id=t["id"], file=Path(t["path"]).name, function=t["function"],
                                timeout_s=t["timeout_s"], labels=t["labels"], contracts=t["contracts"])
                           for t in tests],
                    prepared=prepared, files={name: _sha(path) for name, path in sorted(files.items())})
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    partial = output.with_name(output.name + ".part")
    with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr(MANIFEST, json.dumps(manifest, indent=2) + "\n")
        for name, path in sorted(files.items()):
            bundle.write(path, name)
    partial.replace(output)
    return manifest


def _safe(name):
    path = PurePosixPath(name)
    return name and not path.is_absolute() and ".." not in path.parts and "\\" not in name and ":" not in name


def open_package(path, workdir, gdb=None):
    """Verify and extract a package; return a session for the runner."""
    path = Path(path)
    with zipfile.ZipFile(path) as bundle:
        manifest = json.loads(bundle.read(MANIFEST).decode("utf-8"))
        if manifest.get("schema") != SCHEMA or manifest.get("format") != "ddtt-package":
            raise ValueError("Unsupported prepared run package")
        files = manifest.get("files")
        names = set(bundle.namelist()) - {MANIFEST}
        if not isinstance(files, dict) or names != set(files) or not all(_safe(n) for n in names):
            raise ValueError("Package contents do not match its manifest")
        target = Path(workdir).resolve() / (_sha(path)[:16])
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        for name, digest in files.items():
            data = bundle.read(name)
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError(f"Package file changed: {name}")
            destination = target / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    if hashlib.sha256((target / "firmware.elf").read_bytes()).hexdigest() != manifest["elf_sha256"]:
        raise ValueError("Package ELF does not match its manifest")
    gdb = find_gdb(gdb)
    if not gdb:
        raise FileNotFoundError("GDB with Python not found: pass --gdb or set STM32_GDBTEST_GDB")
    session = dict(root=str(target), out=str(target / "runs"), elf=str(target / "firmware.elf"),
                   profile=str(target / "profile/target.toml"), tests=str(target / manifest["tests_dir"]),
                   gdb=gdb, stand="",
                   package=dict(sha256=_sha(path), name=path.name, created_utc=manifest["created_utc"],
                                tool_version=manifest["tool_version"], prepared=manifest.get("prepared", {})))
    if "build-manifest.json" in files:
        session["build_manifest"] = str(target / "build-manifest.json")
    return session
