"""Portability P1-2: the full-image carrier ELF takes the format and machine of the firmware ELF."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stm32_gdbtest.image import elf_format  # noqa: E402


def header(fmt):
    return f"\nfirmware.elf:     file format {fmt}\n\nSections:\nIdx Name          Size      VMA       LMA\n"


class ElfFormatTests(unittest.TestCase):
    def test_cortex_m_keeps_the_previous_values(self):
        self.assertEqual(elf_format(header("elf32-littlearm")), ("elf32-littlearm", "arm"))

    def test_other_architectures(self):
        self.assertEqual(elf_format(header("elf32-littleriscv")), ("elf32-littleriscv", "riscv"))
        self.assertEqual(elf_format(header("elf64-littleaarch64")), ("elf64-littleaarch64", "aarch64"))

    def test_unknown_or_missing_format_is_refused(self):
        with self.assertRaisesRegex(ValueError, "Unsupported ELF file format"):
            elf_format(header("elf32-avr"))
        with self.assertRaisesRegex(ValueError, "did not report"):
            elf_format("Sections:\n")


if __name__ == "__main__":
    unittest.main()
