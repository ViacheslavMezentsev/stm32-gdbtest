"""Portability P1-1: binutils follow the target prefix of the selected GDB."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stm32_gdbtest.runner import tool  # noqa: E402
from stm32_gdbtest.toolchain import binutil, toolchain_prefix  # noqa: E402


class ToolchainPrefixTests(unittest.TestCase):
    def test_prefix_from_the_gdb_name(self):
        self.assertEqual(toolchain_prefix("/opt/x/bin/arm-none-eabi-gdb-py3"), "arm-none-eabi-")
        self.assertEqual(toolchain_prefix("C:/x/bin/riscv-none-elf-gdb-py3.exe"), "riscv-none-elf-")
        self.assertEqual(toolchain_prefix("/usr/bin/aarch64-linux-gnu-gdb"), "aarch64-linux-gnu-")
        self.assertEqual(toolchain_prefix("/usr/bin/gdb-multiarch"), "")
        self.assertEqual(toolchain_prefix("/usr/bin/gdb"), "")

    def test_binutils_next_to_gdb(self):
        self.assertEqual(Path(binutil("/opt/x/bin/riscv-none-elf-gdb-py3", "objcopy")).name, "riscv-none-elf-objcopy")
        self.assertEqual(Path(binutil("C:/x/bin/riscv-none-elf-gdb-py3.exe", "objdump")).name,
                         "riscv-none-elf-objdump.exe")
        self.assertEqual(Path(binutil("/usr/bin/gdb-multiarch", "objdump")).name, "objdump")

    def test_legacy_prefixed_names_are_kept(self):
        self.assertEqual(tool("/opt/x/bin/arm-none-eabi-gdb-py3", "arm-none-eabi-objdump"),
                         tool("/opt/x/bin/arm-none-eabi-gdb-py3", "objdump"))


if __name__ == "__main__":
    unittest.main()
