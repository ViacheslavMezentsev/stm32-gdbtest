"""GDB lookup shared by doctor and prepared runs (ТЗ 5.17.1, 5.19.4)."""

import os
from pathlib import Path
import shutil


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
