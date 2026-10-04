"""Calls of debugged functions: argument passing, result conversion and refusals."""
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

    def target(self):
        return self


class FakeValue:
    def __init__(self, plain=42, optimized=False, fail_lazy=False):
        self._plain = plain
        self.is_optimized_out = optimized
        self._fail_lazy = fail_lazy
        self.type = FakeType()

    def fetch_lazy(self):
        if self._fail_lazy:
            raise FakeError("lazy fetch refused")

    def __int__(self):
        return int(self._plain)

    def __float__(self):
        return float(self._plain)

    def __bool__(self):
        return bool(self._plain)


class FakeFrame:
    def __init__(self, name="app_loop"):
        self._name = name

    def is_valid(self):
        return True

    def name(self):
        return self._name

    def pc(self):
        return 0x8000100


class CallTests(unittest.TestCase):
    def setUp(self):
        self.expressions = []
        self.result = FakeValue(42)

        def parse(expression):
            self.expressions.append(expression)
            if expression == "app_step":
                return types.SimpleNamespace(type=FakeType())
            return self.result

        self.gdb = types.SimpleNamespace(
            error=FakeError,
            parse_and_eval=parse,
            execute=lambda command, **options: "",
            newest_frame=lambda: FakeFrame(),
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

    def test_call_passes_arguments_by_value(self):
        target = self.target()
        result = target.call("board_delay_ms", 10)
        self.assertEqual(result["operation"], "call")
        self.assertEqual(result["expression"], "board_delay_ms(10)")
        self.assertEqual(result["arguments"], [10])
        self.assertEqual(result["outcome"], "returned")
        self.assertEqual(result["return_value"], 42)
        self.assertEqual(target.report["mutations"][-1]["expression"], "board_delay_ms(10)")

    def test_call_encodes_each_argument_kind(self):
        target = self.target()
        target.call("f", 7, -3, True, 1.5)
        self.assertEqual(self.expressions[-1], "f(7, -3, 1, 1.5)")

    def test_call_without_arguments(self):
        target = self.target()
        result = target.call("app_step")
        self.assertEqual(result["expression"], "app_step()")
        self.assertEqual(result["arguments"], [])

    def test_call_reports_a_void_return(self):
        target = self.target()
        self.gdb.parse_and_eval = lambda expression: types.SimpleNamespace(
            type=FakeType(name="void", code=TYPE_CODE_VOID, size=0)) if expression == "app_step" \
            else self.result
        result = target.call("app_step")
        self.assertEqual(result["return_state"], "void")

    def test_call_refuses_an_invalid_function_name(self):
        target = self.target()
        for function in ("", "board delay", "app_step(", 42, None):
            with self.subTest(function=function):
                with self.assertRaises(ApiError) as caught:
                    target.call(function)
                self.assertEqual(caught.exception.code, "invalid_function")

    def test_call_passes_a_gdb_expression_argument(self):
        target = self.target()
        target.call("app_step", "&app_state", 1)
        self.assertEqual(self.expressions[-1], "app_step(&app_state, 1)")

    def test_call_refuses_an_unsupported_argument(self):
        target = self.target()
        for argument in ("", "7; delete", None, [1], float("inf"), float("nan")):
            with self.subTest(argument=argument):
                with self.assertRaises(ApiError) as caught:
                    target.call("board_delay_ms", argument)
                self.assertEqual(caught.exception.code, "unsupported_argument")
        self.assertEqual(target.report["mutations"], [])

    def test_call_reports_a_refused_expression(self):
        target = self.target()

        def parse(expression):
            raise FakeError("no such function")

        self.gdb.parse_and_eval = parse
        with self.assertRaises(ApiError) as caught:
            target.call("missing_function", 1)
        self.assertEqual(caught.exception.code, "command_failed")
        self.assertIsInstance(caught.exception.__cause__, FakeError)

    def test_call_reports_an_optimized_result(self):
        target = self.target()
        self.gdb.parse_and_eval = lambda expression: types.SimpleNamespace(
            type=FakeType()) if expression == "app_step" else FakeValue(0, optimized=True)
        with self.assertRaises(ApiError) as caught:
            target.call("app_step")
        self.assertEqual(caught.exception.code, "optimized_out")

    def test_call_reports_an_unavailable_result(self):
        target = self.target()
        self.gdb.parse_and_eval = lambda expression: types.SimpleNamespace(
            type=FakeType()) if expression == "app_step" else FakeValue(0, fail_lazy=True)
        with self.assertRaises(ApiError) as caught:
            target.call("app_step")
        self.assertEqual(caught.exception.code, "conversion_failed")


if __name__ == "__main__":
    unittest.main()
