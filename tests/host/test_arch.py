"""Portability P1-7: the architecture adapter reproduces the profile-driven Cortex-M guards and diagnostics."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from stm32_gdbtest import arch  # noqa: E402
from stm32_gdbtest.profile import load_profile  # noqa: E402


class ArchitectureAdapterTests(unittest.TestCase):
    def test_cortex_m_uses_the_profile_lists(self):
        for name in ("f030r8", "f411ce"):
            profile = load_profile(ROOT / "tests/firmware/profiles" / name / "target.toml")
            adapter = arch.adapter("arm")
            self.assertEqual(adapter.fault_guards(profile), profile["fault_handlers"])
            self.assertEqual(adapter.diagnostic_registers(profile), profile["core_registers"])
            self.assertEqual(adapter.diagnostic_memory(profile), profile["diagnostic_registers"])

    def test_missing_machine_means_cortex_m_and_unknown_is_refused(self):
        self.assertIs(arch.adapter(None), arch.adapter("arm"))
        with self.assertRaisesRegex(ValueError, "Unsupported target architecture: riscv"):
            arch.adapter("riscv")


if __name__ == "__main__":
    unittest.main()
