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


class Register:
    def __init__(self, name):
        self.name = name


class Frame:
    """GDB frame stand-in: registers by exact name, like the target description of the server."""
    def __init__(self, values, broken_architecture=False):
        self.values, self.broken = values, broken_architecture

    def read_register(self, name):
        if name not in self.values:
            raise ValueError(f"Bad register: {name}")
        return self.values[name]

    def architecture(self):
        if self.broken:
            raise RuntimeError("no architecture")
        values = self.values
        return type("Arch", (), {"registers": lambda self: [Register(n) for n in values]})()


class NamedRegisterTests(unittest.TestCase):
    def test_exact_name_is_read_as_is(self):
        self.assertEqual(arch.read_named_register(Frame({"xPSR": 0x2100000F}), "xPSR"), (0x2100000F, "xPSR"))

    def test_name_differing_in_case_is_resolved(self):
        self.assertEqual(arch.read_named_register(Frame({"xpsr": 0x2100000F, "pc": 4}), "xPSR"), (0x2100000F, "xpsr"))

    def test_signed_register_type_is_read_as_unsigned(self):
        value = type("Value", (), {"type": type("Type", (), {"sizeof": 4})(), "__int__": lambda self: -0x7F000000})()
        self.assertEqual(arch.read_named_register(Frame({"xPSR": value}), "xPSR"), (0x81000000, "xPSR"))

    def test_missing_or_ambiguous_register_keeps_the_original_error(self):
        for frame in (Frame({"pc": 4}), Frame({"xpsr": 1, "XPSR": 2}), Frame({"xpsr": 1}, broken_architecture=True)):
            with self.subTest(names=sorted(frame.values)), self.assertRaisesRegex(ValueError, "Bad register: xPSR"):
                arch.read_named_register(frame, "xPSR")


if __name__ == "__main__":
    unittest.main()
