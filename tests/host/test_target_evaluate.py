"""evaluate conversions and named register reads, with only the GDB surface substituted."""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import ApiError
from stm32_gdbtest.configuration import DEFAULTS, Configuration, freeze

TYPE_CODE_INT, TYPE_CODE_FLT, TYPE_CODE_BOOL, TYPE_CODE_VOID = 8, 12, 11, 10


class FakeError(Exception):
    pass


class FakeType:
    def __init__(self, code=TYPE_CODE_INT, size=4, name="uint32_t"):
        self.code = code
        self.sizeof = size
        self.name = name


class FakeValue:
    def __init__(self, plain=7, code=TYPE_CODE_INT, size=4, optimized=False, fail_lazy=False):
        self._plain = plain
        self.type = FakeType(code, size)
        self.is_optimized_out = optimized
        self._fail_lazy = fail_lazy

    def fetch_lazy(self):
        if self._fail_lazy:
            raise FakeError("lazy fetch refused")

    def __int__(self):
        return int(self._plain)

    def __float__(self):
        return float(self._plain)

    def __bool__(self):
        return bool(self._plain)

    def string(self):
        return str(self._plain)


class FakeFrame:
    def __init__(self, registers=None):
        self._registers = registers or {}

    def is_valid(self):
        return True

    def name(self):
        return "app_loop"

    def pc(self):
        if "pc" in self._registers:
            value = self._registers["pc"]
            if isinstance(value, Exception):
                raise value
            return value
        return 0x8000100

    def return_type(self):
        return FakeType()

    def read_register(self, name):
        if name not in self._registers:
            # GDB raises a plain ValueError for an unknown register name.
            raise ValueError(f"Bad register: {name}")
        value = self._registers[name]
        if isinstance(value, Exception):
            raise value
        return value


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.value = FakeValue(7)
        self.frame = FakeFrame()

        def parse(expression):
            if expression == "boom":
                raise FakeError("no symbol")
            return self.value

        self.gdb = types.SimpleNamespace(
            error=FakeError,
            parse_and_eval=parse,
            newest_frame=lambda: self.frame,
            execute=lambda command, **options: "",
            events=types.SimpleNamespace(stop=Mock()),
        )

    def target(self):
        import builtins
        real_import = builtins.__import__

        def importing_gdb(name, *arguments, **options):
            if name == "gdb":
                return self.gdb
            return real_import(name, *arguments, **options)

        saved = {name: sys.modules.pop(name, None)
                 for name in ("stm32_gdbtest.target", "stm32_gdbtest.values")}
        with patch.object(builtins, "__import__", side_effect=importing_gdb):
            module = importlib.import_module("stm32_gdbtest.target")
        for name, previous in saved.items():
            sys.modules.pop(name, None)
            if previous is not None:
                sys.modules[name] = previous
        configuration = Configuration(
            freeze(dict(target={}, image=None, api=dict(schema=1, records=dict(DEFAULTS)))),
            freeze(dict(target=None, api=None, image=None)), None, {})
        return module.Target({"checks": [], "evaluations": []},
                             {"breakpoint_limit": 4, "fault_handlers": []}, configuration)

    def test_evaluate_keeps_the_declared_type(self):
        target = self.target()
        self.assertEqual(target.evaluate("app_state.ticks"), 7)
        self.assertEqual(target.report["evaluations"], [])

    def test_evaluate_converts_on_request(self):
        target = self.target()
        self.assertEqual(target.evaluate("ratio", as_type=float), 7.0)
        self.assertIsInstance(target.evaluate("ratio", as_type=float), float)
        self.assertIsInstance(target.evaluate("on", as_type=bool), bool)
        self.assertEqual(target.evaluate("counter", as_type="int"), 7)
        entry = target.report["evaluations"][-1]
        self.assertEqual(entry["value_type"], "int")
        self.assertEqual(entry["expression"], "counter")

    def test_evaluate_reports_an_unconvertible_value(self):
        target = self.target()
        self.value = FakeValue("label", TYPE_CODE_INT, 4)
        # int("label") is impossible, so the conversion failure is reported, not the expression.
        with self.assertRaises(ApiError) as caught:
            target.evaluate("text", as_type=int)
        # Converting the value fails inside GDB, so the failure is a conversion one.
        self.assertEqual(caught.exception.code, "conversion_failed")
        self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_evaluate_rejects_invalid_input(self):
        target = self.target()
        for expression in ("", "   ", 7, None):
            with self.subTest(expression=expression):
                with self.assertRaises(ApiError) as caught:
                    target.evaluate(expression)
                self.assertEqual(caught.exception.code, "invalid_expression")
        with self.assertRaises(ApiError) as caught:
            target.evaluate("x", as_type=str)
        self.assertEqual(caught.exception.code, "unsupported_type")

    def test_evaluate_reports_a_failed_expression(self):
        target = self.target()
        with self.assertRaises(ApiError) as caught:
            target.evaluate("boom")
        self.assertEqual(caught.exception.code, "command_failed")
        self.assertIsInstance(caught.exception.__cause__, FakeError)

    def test_evaluate_reports_an_optimized_value(self):
        target = self.target()
        self.value = FakeValue(0, optimized=True)
        with self.assertRaises(ApiError) as caught:
            target.evaluate("gone")
        self.assertEqual(caught.exception.code, "optimized_out")

    def test_registers_reads_names_by_frame(self):
        target = self.target()
        self.frame = FakeFrame({"pc": 0x8000100, "sp": FakeValue(0x20001fe8, TYPE_CODE_INT, 4),
                                "r0": FakeValue(42, TYPE_CODE_INT, 4)})
        self.assertEqual(target.registers("pc", "sp", "r0"),
                         {"pc": 0x8000100, "sp": 0x20001fe8, "r0": 42})

    def test_registers_masks_by_declared_width(self):
        target = self.target()
        self.frame = FakeFrame({"sp": FakeValue(0x1FFFFFFFF, TYPE_CODE_INT, 4)})
        self.assertEqual(target.registers("sp"), {"sp": 0xFFFFFFFF})
        self.frame = FakeFrame({"r0": FakeValue(0x1FF, TYPE_CODE_INT, 1)})
        self.assertEqual(target.registers("r0"), {"r0": 0xFF})

    def test_registers_prefers_the_frame_pc(self):
        target = self.target()
        self.frame = FakeFrame({"pc": 0x8000200, "r0": FakeValue(1, TYPE_CODE_INT, 4)})
        self.assertEqual(target.registers("pc", "r0"), {"pc": 0x8000200, "r0": 1})

    def test_registers_refuse_missing_names(self):
        target = self.target()
        self.frame = FakeFrame({"r0": FakeValue(1, TYPE_CODE_INT, 4)})
        with self.assertRaises(ApiError) as caught:
            target.registers("r0", "r9")
        self.assertEqual(caught.exception.code, "read_failed")
        self.assertIsInstance(caught.exception.__cause__, ValueError)

    def test_registers_reject_invalid_arguments(self):
        target = self.target()
        with self.assertRaises(ApiError) as caught:
            target.registers()
        self.assertEqual(caught.exception.code, "invalid_names")
        for name in ("", 7, None):
            with self.subTest(name=name):
                with self.assertRaises(ApiError) as caught:
                    target.registers(name)
                self.assertEqual(caught.exception.code, "invalid_names")

    def test_registers_reject_an_invalid_frame(self):
        target = self.target()
        broken = types.SimpleNamespace(is_valid=lambda: False)

        def fail():
            raise AssertionError("newest_frame must not be used for an explicit frame")

        self.gdb.newest_frame = fail
        with self.assertRaises(ApiError) as caught:
            target.registers("r0", frame=broken)
        self.assertEqual(caught.exception.code, "no_frame")


if __name__ == "__main__":
    unittest.main()
