"""Environment smoke check of the CI image; firmware projects are checked by ci/run_checks.py."""

import json
import os
from pathlib import Path
import subprocess


def output(*args):
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()


def main():
    lock = json.loads(Path(__file__).with_name("dependencies.lock.json").read_text())
    print(f"Selected GCC={os.environ['GCC_VERSION']} CMake={os.environ['CMAKE_VERSION']}", flush=True)
    assert Path(output("which", "arm-none-eabi-gcc")).parent == Path(os.environ["ARM_TOOLCHAIN_ROOT"]) / "bin"
    assert output("ninja", "--version") == lock["ninja_version"]
    python = tuple(int(x) for x in output("python3", "-c", "import sys; print(*sys.version_info[:2])").split())
    assert python >= (3, 11), python
    for cmake in lock["cmake_versions"]:
        assert output(f"/opt/cmake-{cmake}/bin/cmake", "--version").splitlines()[0] == f"cmake version {cmake}"
    for gcc in lock["gcc_versions"]:
        bin_dir = Path(f"/opt/xpack-arm-none-eabi-gcc-{gcc}/bin")
        assert output(str(bin_dir / "arm-none-eabi-gcc"), "-dumpfullversion") == gcc.split("-")[0]
        for tool in ("objcopy", "objdump"):
            print(output(str(bin_dir / f"arm-none-eabi-{tool}"), "--version").splitlines()[0], flush=True)
        # stm32-gdbtest needs GDB with embedded Python >= 3.11 (tomllib in the agent).
        probe = output(str(bin_dir / "arm-none-eabi-gdb-py3"), "-nx", "-batch", "-ex",
                       "python import sys, tomllib, gdb; print(sys.version.split()[0], gdb.VERSION)")
        print(f"GCC {gcc}: GDB-Python {probe}", flush=True)
    for source in lock["sources"]:
        destination = Path(source["destination"])
        head = output("git", "-c", f"safe.directory={destination}", "-C", str(destination), "rev-parse", "HEAD")
        assert head == source["commit"], (source["name"], head)
        for filename in source["required_files"]:
            assert (destination / filename).is_file(), str(destination / filename)
    print("PASS environment", flush=True)


if __name__ == "__main__":
    main()
