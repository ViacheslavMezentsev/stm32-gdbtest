"""Portability P1-8: build manifest recognition rules kept in one place; STM32 results unchanged."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stm32_gdbtest.build_manifest import label, version_macros  # noqa: E402


class ManifestRuleTests(unittest.TestCase):
    def test_installation_labels(self):
        root = Path("/work/project")
        self.assertEqual(label("/opt/STM32Cube_FW_F4_V1.28.0/Drivers/x.h", root), "STM32Cube_FW_F4_V1.28.0/Drivers/x.h")
        self.assertEqual(label("/opt/xpack-arm-none-eabi-gcc-13.3.1-1.1/lib/a.h", root),
                         "xpack-arm-none-eabi-gcc-13.3.1-1.1/lib/a.h")
        self.assertEqual(label("/opt/xpack-riscv-none-elf-gcc-14.2.0-3/lib/a.h", root),
                         "xpack-riscv-none-elf-gcc-14.2.0-3/lib/a.h")
        self.assertEqual(label("/opt/vendor/sdk/a.h", root), "external/a.h")

    def test_version_macros(self):
        text = ("#define __STM32F4xx_HAL_VERSION_MAIN (0x01U)\n#define __CM4_CMSIS_VERSION_SUB 5\n"
                "#define __OTHER_VERSION_MAIN 1\n")
        self.assertEqual(version_macros(text), {"__STM32F4xx_HAL_VERSION_MAIN": 1, "__CM4_CMSIS_VERSION_SUB": 5})


if __name__ == "__main__":
    unittest.main()
