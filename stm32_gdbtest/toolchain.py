"""GDB lookup shared by doctor and prepared runs (ТЗ 5.17.1, 5.19.4)."""

import os
from pathlib import Path
import re
import shutil

_PERCENT = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")
_UNEXPANDED = re.compile(r"%[A-Za-z_][A-Za-z0-9_]*%|\$\{?[A-Za-z_]")


def expand_path(value):
    """Local stand path (ТЗ 3.4.12): ~, %VAR% and $VAR/${VAR} on every OS.

    A stand file can then say "%USERPROFILE%/.ssh/key" or "~/.ssh/key" instead of a
    personal absolute path. A variable that is not set is an error, not an empty string.
    """
    expanded = _PERCENT.sub(lambda m: os.environ.get(m[1], m[0]), str(value))
    expanded = os.path.expanduser(os.path.expandvars(expanded))
    if _UNEXPANDED.search(expanded):
        raise ValueError(f"Environment variable in path is not set: {value}")
    return expanded


def toolchain_gdb():
    """The toolchain run_hw.py and the CI firmware use: ARM_TOOLCHAIN_ROOT, then the Windows default."""
    roots = [os.environ.get("ARM_TOOLCHAIN_ROOT")]
    if os.name == "nt" and os.environ.get("USERPROFILE"):
        roots.append(str(Path(os.environ["USERPROFILE"]) / "xpack-arm-none-eabi-gcc-13.3.1-1.1"))
    suffix = ".exe" if os.name == "nt" else ""
    for root in filter(None, roots):
        candidate = Path(root) / "bin" / ("arm-none-eabi-gdb-py3" + suffix)
        if candidate.is_file():
            return str(candidate)
    return None


def find_gdb(explicit=None):
    """--gdb → STM32_GDBTEST_GDB → PATH (gdb-py3, gdb) → toolchain root; None when absent."""
    return (explicit or os.environ.get("STM32_GDBTEST_GDB") or shutil.which("arm-none-eabi-gdb-py3")
            or shutil.which("arm-none-eabi-gdb") or toolchain_gdb())
