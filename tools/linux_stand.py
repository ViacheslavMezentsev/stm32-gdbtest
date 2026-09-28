#!/usr/bin/env python3
"""Linux stand environment for stm32-gdbtest without root or system changes.

Installs the pinned tools of tools/linux-stand.lock.json into a user prefix
(default ~/.local/stm32-gdbtest): Python 3.11 (python-build-standalone), CMake,
Ninja, xPack GNU Arm GCC with GDB-Python, xPack OpenOCD, and CMSIS from the Cube
packages pinned in ci/dependencies.lock.json. Each download is checked against its
SHA-256. The system Python only runs this script, so Python 3.8 (Ubuntu 20.04) is
enough; the module itself then runs on the installed Python 3.11.

Requirements: curl, tar, git; x86_64 or aarch64 with glibc >= 2.31.
J-Link software, udev rules and dialout/plugdev membership are installed by the
owner of the machine (see docs/en/LINUX_STAND.md).

Usage (repository root):
  python3 tools/linux_stand.py install [--prefix DIR] [--only NAME ...]
  python3 tools/linux_stand.py verify  [--prefix DIR]
  . ~/.local/stm32-gdbtest/env.sh
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "tools/linux-stand.lock.json"
CI_LOCK = ROOT / "ci/dependencies.lock.json"
MARKER = ".stm32-gdbtest.sha256"
ARCHES = {"x86_64": "x86_64", "amd64": "x86_64", "aarch64": "aarch64", "arm64": "aarch64"}


def say(text):
    print(text, flush=True)


def run(*args, cwd=None):
    say("$ " + " ".join(str(a) for a in args))
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)


def run_network(*args, attempts=4):
    """Network commands survive transient server errors (e.g. HTTP 500 of GitHub releases)."""
    for attempt in range(1, attempts + 1):
        say("$ " + " ".join(str(a) for a in args))
        if subprocess.run([str(a) for a in args]).returncode == 0:
            return
        if attempt < attempts:
            delay = 15 * 2 ** (attempt - 1)
            say(f"Attempt {attempt} of {attempts} failed; retrying in {delay} s")
            time.sleep(delay)
    sys.exit("Network command failed after {} attempts: {}".format(attempts, " ".join(str(a) for a in args)))


def machine():
    arch = ARCHES.get(platform.machine().lower())
    if sys.platform != "linux" or not arch:
        sys.exit(f"Unsupported host {sys.platform}/{platform.machine()}: Linux x86_64 or aarch64 required")
    libc, version = platform.libc_ver()
    if libc == "glibc" and tuple(int(x) for x in version.split(".")[:2]) < (2, 31):
        sys.exit(f"glibc {version} is older than 2.31 (Ubuntu 20.04)")
    return arch


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def install_component(prefix, component, arch):
    archive = component["archives"][arch]
    destination = prefix / component["directory"]
    marker = destination / MARKER
    if marker.is_file() and marker.read_text().strip() == archive["sha256"]:
        say(f"{component['name']} {component['version']}: already installed")
        return
    say(f"{component['name']} {component['version']}: {archive['url']}")
    downloads = prefix / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    file = downloads / archive["url"].rsplit("/", 1)[1]
    if not file.is_file() or sha256(file) != archive["sha256"]:
        partial = file.with_name(file.name + ".part")
        run_network("curl", "--fail", "--silent", "--show-error", "--location", "--retry", "5", "--retry-delay",
                    "5", "--connect-timeout", "30", "--max-time", "1800", "--output", partial, archive["url"])
        actual = sha256(partial)
        if actual != archive["sha256"]:
            partial.unlink()
            sys.exit(f"SHA-256 mismatch for {component['name']}: {actual}")
        partial.replace(file)
    if destination.exists():
        shutil.rmtree(destination)
    staging = Path(tempfile.mkdtemp(prefix=".install-", dir=prefix))
    try:
        if component["kind"] == "tar":
            run("tar", "-xzf", file, "--strip-components=1", "-C", staging)
        elif component["kind"] == "zip":
            with zipfile.ZipFile(file) as bundle:
                for info in bundle.infolist():
                    target = staging / info.filename
                    bundle.extract(info, staging)
                    mode = info.external_attr >> 16
                    target.chmod(mode & 0o777 if mode else 0o755)
        else:
            sys.exit(f"Unknown archive kind: {component['kind']}")
        if not (staging / component["check"]).is_file():
            sys.exit(f"{component['name']}: {component['check']} missing after extraction")
        (staging / MARKER).write_text(archive["sha256"] + "\n")
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging.rename(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def install_source(prefix, item):
    """Pinned sparse checkout; core.sparseCheckout keeps it compatible with git 2.25."""
    destination = prefix / "STM32Cube/Repository" / Path(item["destination"]).name
    marker = destination / MARKER
    if marker.is_file() and marker.read_text().strip() == item["commit"]:
        say(f"{item['name']}: already installed")
        return
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    git = ["git", "-C", destination]
    run(*git, "init", "--quiet")
    run(*git, "remote", "add", "origin", item["url"])
    # git 2.25 accepts fetch --filter only with an explicit partial-clone promisor.
    run(*git, "config", "core.repositoryformatversion", "1")
    run(*git, "config", "extensions.partialClone", "origin")
    run(*git, "config", "core.sparseCheckout", "true")
    sparse = destination / ".git/info/sparse-checkout"
    sparse.parent.mkdir(parents=True, exist_ok=True)
    sparse.write_text("".join(f"/{name}/\n" for name in item["sparse_include"]))
    run_network(*git, "fetch", "--quiet", "--depth=1", "--filter=blob:none", "origin", item["commit"])
    run(*git, "checkout", "--quiet", "--detach", "FETCH_HEAD")
    head = subprocess.check_output([str(a) for a in git] + ["rev-parse", "HEAD"], text=True).strip()
    if head != item["commit"]:
        sys.exit(f"Unexpected commit for {item['name']}: {head}")
    if item["submodules"]:
        run_network(*git, "submodule", "update", "--init", "--depth=1", "--", *item["submodules"])
    for filename in item["required_files"]:
        if not (destination / filename).is_file():
            sys.exit(f"{item['name']}: {filename} missing")
    marker.write_text(item["commit"] + "\n")


def paths(prefix, lock):
    directory = {c["name"]: prefix / c["directory"] for c in lock["components"]}
    return directory, prefix / "STM32Cube/Repository"


def write_env(prefix, lock):
    directory, cube = paths(prefix, lock)
    gcc = directory["gcc"]
    lines = [
        "# Generated by tools/linux_stand.py; source it: . " + str(prefix / "env.sh"),
        f"export STM32_GDBTEST_PREFIX='{prefix}'",
        "export PATH='" + ":".join(str(p) for p in (
            directory["python"] / "bin", directory["cmake"] / "bin", directory["ninja"],
            gcc / "bin", directory["openocd"] / "bin")) + "':\"$PATH\"",
        f"export ARM_TOOLCHAIN_ROOT='{gcc}'",
        f"export STM32CUBE_REPOSITORY='{cube}'",
        f"export STM32_GDBTEST_GDB='{gcc / 'bin/arm-none-eabi-gdb-py3'}'",
        "",
    ]
    (prefix / "env.sh").write_text("\n".join(lines))
    say(f"Environment: . {prefix / 'env.sh'}")


def verify(prefix, lock, arch):
    directory, _ = paths(prefix, lock)
    python = directory["python"] / "bin/python3.11"
    checks = [
        [python, "-c", "import sys, tomllib; print('Python', sys.version.split()[0])"],
        [directory["cmake"] / "bin/cmake", "--version"],
        [directory["ninja"] / "ninja", "--version"],
        [directory["gcc"] / "bin/arm-none-eabi-gcc", "-dumpfullversion"],
        [directory["gcc"] / "bin/arm-none-eabi-gdb-py3", "-nx", "-batch", "-ex",
         "python import sys, tomllib, gdb; print('GDB', gdb.VERSION, 'Python', sys.version.split()[0])"],
        [directory["openocd"] / "bin/openocd", "--version"],
    ]
    failed = False
    for check in checks:
        result = subprocess.run([str(a) for a in check], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        first = (result.stdout.strip().splitlines() or [""])[0]
        failed |= result.returncode != 0
        say(("OK   " if result.returncode == 0 else "FAIL ") + f"{Path(check[0]).name}: {first}")
    say(f"Host: {platform.system()} {platform.release()} {arch}, glibc {platform.libc_ver()[1]}")
    return 1 if failed else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("install", "verify"))
    parser.add_argument("--prefix", type=Path, default=Path(os.environ.get(
        "STM32_GDBTEST_PREFIX", "~/.local/stm32-gdbtest")))
    parser.add_argument("--only", nargs="+", metavar="NAME",
                        help="subset: python cmake ninja gcc openocd cube")
    args = parser.parse_args()
    arch = machine()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    prefix = args.prefix.expanduser().resolve()
    names = [c["name"] for c in lock["components"]] + ["cube"]
    unknown = sorted(set(args.only or []) - set(names))
    if unknown:
        sys.exit("Unknown component: " + ", ".join(unknown))
    selected = set(args.only or names)
    if args.command == "install":
        for tool in ("curl", "tar", "git"):
            if not shutil.which(tool):
                sys.exit(f"{tool} is required (sudo apt install {tool})")
        prefix.mkdir(parents=True, exist_ok=True)
        for component in lock["components"]:
            if component["name"] in selected:
                install_component(prefix, component, arch)
        if "cube" in selected:
            sources = {s["name"]: s for s in json.loads(CI_LOCK.read_text(encoding="utf-8"))["sources"]}
            for name in lock["cube_sources"]:
                install_source(prefix, sources[name])
        write_env(prefix, lock)
    return verify(prefix, lock, arch)


if __name__ == "__main__":
    sys.exit(main())
