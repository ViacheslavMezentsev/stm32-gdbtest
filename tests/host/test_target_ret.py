"""Forced returns: typed values, expression form, range refusal and the 0.2.x alias."""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import ApiError
from stm32_gdbtest.configuration import Configuration, DEFAULTS, freeze

TYPE_CODE_INT, TYPE_CODE_BOOL, TYPE_CODE_VOID = 8, 11, 10


class FakeError(Exception):
    pass


class FakeType:
    def __init__(self, name="uint32_t", code=TYPE_CODE_INT, size=4):
        self.name = name
        self.code = code
        self.sizeof = size


class FakeFrame:
    def __init__(self, name="app_step", caller="app_receiver_step", kind=None):
        self._name = name
        self._caller = caller
        self._kind = kind or FakeType()

    def is_valid(self):
        return True

    def name(self):
        return self._name

    def pc(self):
        return 0x8000100

    def return_type(self):
        return self._kind

    def older(self):
        return FakeFrame(self._caller, None, self._kind) if self._caller else None


class RetTests(unittest.TestCase):
    def setUp(self):
        self.executed = []
        self.frame = FakeFrame()

        def execute(command, **options):
            self.executed.append(command)
            return ""

        self.gdb = types.SimpleNamespace(
            error=FakeError,
            parse_and_eval=lambda expression: types.SimpleNamespace(
                is_optimized_out=False, fetch_lazy=lambda: None, __int__=lambda self: 0),
            execute=execute,
            newest_frame=lambda: self.frame,
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
        return module.Target({"checks": [], "mutations": []},
                             {"breakpoint_limit": 4, "fault_handlers": []}, configuration)

    def test_ret_encodes_the_declared_type(self):
        target = self.target()
        result = target.ret(42)
        self.assertEqual(result["outcome"], "forced")
        self.assertEqual(result["function"], "app_step")
        self.assertEqual(result["caller"], "app_receiver_step")
        self.assertEqual(result["applied"], 42)
        self.assertEqual(result["type_name"], "uint32_t")
        self.assertEqual(result["command"], "return (uint32_t)0x2a")
        self.assertEqual(self.executed[-1], "return (uint32_t)0x2a")
        self.assertEqual(target.report["mutations"][-1]["value"], 42)

    def test_ret_accepts_zero_and_a_bare_return(self):
        target = self.target()
        self.assertEqual(target.ret(0)["command"], "return (uint32_t)0x0")
        bare = target.ret()
        self.assertEqual(bare["command"], "return")
        self.assertIsNone(bare["applied"])
        self.assertEqual(self.executed[-1], "return")

    def test_ret_accepts_a_gdb_expression(self):
        target = self.target()
        result = target.ret("(unsigned long)0x2a")
        self.assertEqual(result["command"], "return (unsigned long)0x2a")
        self.assertIsNone(result["applied"])

    def test_ret_refuses_a_value_outside_the_declared_width(self):
        target = self.target()
        self.frame = FakeFrame(kind=FakeType(name="int8_t", size=1))
        for value in (128, -129):
            with self.subTest(value=value):
                with self.assertRaises(ApiError) as caught:
                    target.ret(value)
                self.assertEqual(caught.exception.code, "out_of_range")
                self.assertEqual(caught.exception.details["low"], -128)
                self.assertEqual(caught.exception.details["high"], 127)
        self.assertEqual(target.ret(-128)["command"], "return (int8_t)-0x80")
        self.assertEqual(target.ret(127)["applied"], 127)

    def test_ret_treats_an_enum_and_a_bool_as_unsigned(self):
        target = self.target()
        self.frame = FakeFrame(kind=FakeType(name="bool", code=TYPE_CODE_BOOL, size=1))
        self.assertEqual(target.ret(1)["command"], "return (bool)0x1")
        with self.assertRaises(ApiError) as caught:
            target.ret(2)
        self.assertEqual(caught.exception.code, "out_of_range")

    def test_ret_takes_signedness_from_the_declared_type(self):
        # `size_t` carries no `uint` prefix; `Type.is_signed` (GDB 12+) decides, not the name.
        target = self.target()
        kind = FakeType(name="size_t", size=4)
        kind.is_signed = False
        self.frame = FakeFrame(kind=kind)
        self.assertEqual(target.ret(0xFFFFFFFF)["command"], "return (size_t)0xffffffff")
        signed = FakeType(name="my_count_t", size=2)
        signed.is_signed = True
        self.frame = FakeFrame(kind=signed)
        with self.assertRaises(ApiError) as caught:
            target.ret(0x8000)
        self.assertEqual(caught.exception.details["high"], 0x7FFF)

    def test_ret_rejects_an_unsupported_return_type(self):
        target = self.target()
        self.frame = FakeFrame(kind=FakeType(name="void", code=TYPE_CODE_VOID, size=0))
        with self.assertRaises(ApiError) as caught:
            target.ret(1)
        self.assertEqual(caught.exception.code, "unsupported_type")
        self.assertEqual(caught.exception.details["type_name"], "void")

    def test_ret_rejects_a_non_integer_value(self):
        target = self.target()
        for value in (1.5, True, [1]):
            with self.subTest(value=value):
                with self.assertRaises(ApiError) as caught:
                    target.ret(value)
                self.assertEqual(caught.exception.code, "unsupported_type")

    def test_ret_reports_a_refused_command(self):
        target = self.target()

        def execute(command, **options):
            raise FakeError("cannot force return")

        self.gdb.execute = execute
        with self.assertRaises(ApiError) as caught:
            target.ret(1)
        self.assertEqual(caught.exception.code, "command_failed")
        self.assertIsInstance(caught.exception.__cause__, FakeError)

if __name__ == "__main__":
    unittest.main()
