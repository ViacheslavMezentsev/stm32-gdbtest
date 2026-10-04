"""Typed read/write of debugged objects, with only the GDB surface substituted.

The fake GDB exposes exactly the operations the implementation uses: `parse_and_eval`, `execute`,
type objects with codes and fields, and values that convert to plain Python types.
"""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import ApiError
from stm32_gdbtest.configuration import Configuration, DEFAULTS, freeze

TYPE_CODE_INT, TYPE_CODE_FLT, TYPE_CODE_STRING, TYPE_CODE_BOOL = 8, 12, 15, 11
TYPE_CODE_ARRAY, TYPE_CODE_STRUCT, TYPE_CODE_REF = 16, 13, 17
# The fake GDB defines the same names GDB does; the implementation reads its own stable code table.


class FakeType:
    def __init__(self, code, fields=None, bounds=None):
        self.code = code
        self._fields = fields or []
        self._bounds = bounds

    def strip_typedefs(self):
        return self

    def fields(self):
        if not self._fields:
            raise RuntimeError("not a struct")
        return [types.SimpleNamespace(name=name) for name in self._fields]

    def range(self):
        return self._bounds


class FakeValue:
    def __init__(self, plain, code=TYPE_CODE_INT, fields=None, children=None, bounds=None,
                 optimized=False, fail_lazy=False):
        self._plain = plain
        self.type = FakeType(code, fields, bounds)
        self._children = children or {}
        self.is_optimized_out = optimized
        self._fail_lazy = fail_lazy

    def fetch_lazy(self):
        if self._fail_lazy:
            raise FakeError("lazy fetch refused")

    def string(self):
        return self._plain

    def __int__(self):
        return int(self._plain)

    def __float__(self):
        return float(self._plain)

    def __bool__(self):
        return bool(self._plain)

    def __getitem__(self, key):
        return self._children[key]


class FakeError(Exception):
    pass


class ReadWriteTests(unittest.TestCase):
    def setUp(self):
        self.integer = FakeValue(41)
        self.floating = FakeValue(1.5, TYPE_CODE_FLT)
        self.text = FakeValue("hello", TYPE_CODE_STRING)
        self.struct = FakeValue({"ticks": FakeValue(7), "led": FakeValue(1)}, TYPE_CODE_STRUCT,
                                fields=["ticks", "led"],
                                children={"ticks": FakeValue(7), "led": FakeValue(1)})
        self.array = FakeValue([FakeValue(10), FakeValue(20), FakeValue(30)], TYPE_CODE_ARRAY,
                               bounds=(0, 2),
                               children={0: FakeValue(10), 1: FakeValue(20), 2: FakeValue(30)})
        self.optimized = FakeValue(0, optimized=True)
        self.refused = FakeValue(0, fail_lazy=True)
        self.memory = {"app_state.ticks": self.integer}

        def parse(expression):
            # The memory map holds whole expressions; member reads are registered as dotted keys.
            return self.memory[expression]

        def execute(command, **options):
            if "app_delay" in command:
                raise FakeError("read-only memory")
            return ""

        self.gdb = types.SimpleNamespace(
            error=FakeError,
            parse_and_eval=parse,
            execute=execute,
            TYPE_CODE_INT=TYPE_CODE_INT,
            TYPE_CODE_FLT=TYPE_CODE_FLT,
            TYPE_CODE_STRING=TYPE_CODE_STRING,
            TYPE_CODE_ARRAY=TYPE_CODE_ARRAY,
            TYPE_CODE_STRUCT=TYPE_CODE_STRUCT,
            TYPE_CODE_UNION=14,
            TYPE_CODE_BOOL=11,
            TYPE_CODE_CHAR=9,
            TYPE_CODE_ENUM=10,
            events=types.SimpleNamespace(stop=Mock()),
        )

    def target(self):
        """Import the target module with a GDB substitute that survives a cached `import gdb`.

        A full host run imports the real modules earlier, and `import gdb` resolves through the import
        machinery, so the substitute is installed at the import level for the duration of the call.
        """
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
        return module.Target({"checks": []}, {}, configuration)

    def test_read_returns_plain_types(self):
        target = self.target()
        self.memory = {"app_state.ticks": self.integer}
        self.assertEqual(target.read("app_state.ticks"), 41)
        self.memory = {"ratio": self.floating}
        self.assertIsInstance(target.read("ratio"), float)
        self.assertEqual(target.read("ratio"), 1.5)
        self.memory = {"ready": FakeValue(1, TYPE_CODE_BOOL)}
        self.assertIsInstance(target.read("ready"), bool)
        self.assertIs(target.read("ready"), True)
        self.memory = {"name": self.text}
        self.assertEqual(target.read("name"), "hello")

    def test_read_array_slice_and_struct(self):
        target = self.target()
        self.memory = {"samples": self.array}
        self.assertEqual(target.read("samples"), [10, 20, 30])
        self.assertEqual(target.read("samples", start=1, count=1), [20])
        self.memory = {"app_state": self.struct, "(app_state).ticks": FakeValue(7)}
        self.assertEqual(target.read("app_state"), {"ticks": 7, "led": 1})
        self.assertEqual(target.read("app_state", fields={"ticks": None}), {"ticks": 7})

    def test_read_rejects_invalid_input(self):
        target = self.target()
        for path in ("", 7, None):
            with self.assertRaises(ApiError) as caught:
                target.read(path)
            self.assertEqual(caught.exception.code, "invalid_path")
        with self.assertRaises(ApiError) as caught:
            target.read("app_state", fields={})
        self.assertEqual(caught.exception.code, "invalid_fields")
        with self.assertRaises(ApiError) as caught:
            target.read("app_state", fields={1: None})
        self.assertEqual(caught.exception.code, "invalid_fields")

    def test_read_reports_optimized_and_refused_values(self):
        target = self.target()
        self.memory = {"gone": self.optimized}
        with self.assertRaises(ApiError) as caught:
            target.read("gone")
        self.assertEqual(caught.exception.code, "optimized_out")
        self.memory = {"bad": self.refused}
        with self.assertRaises(ApiError) as caught:
            target.read("bad")
        self.assertEqual(caught.exception.code, "conversion_failed")
        self.assertIsInstance(caught.exception.__cause__, FakeError)

    def test_read_rejects_a_slice_of_a_non_array(self):
        target = self.target()
        self.memory = {"app_state.ticks": self.integer}
        with self.assertRaises(ApiError) as caught:
            target.read("app_state.ticks", count=2)
        self.assertEqual(caught.exception.code, "unsupported_type")

    def test_write_verifies_and_logs_the_mutation(self):
        target = self.target()
        written = {}

        def execute(command, **options):
            written["command"] = command
            self.integer._plain = 42
            return ""

        self.gdb.execute = execute
        result = target.write("app_state.ticks", 42)
        self.assertEqual(result["before"], 41)
        self.assertEqual(result["after"], 42)
        self.assertTrue(result["verified"])
        self.assertIn("set variable app_state.ticks = 42", written["command"])
        self.assertEqual(target.report["mutations"][0]["after"], 42)

    def test_write_reports_a_failed_read_back(self):
        target = self.target()
        with self.assertRaises(ApiError) as caught:
            target.write("app_state.ticks", 42)
        self.assertEqual(caught.exception.code, "verification_failed")
        self.assertEqual(caught.exception.details["effect"], "partial")
        self.assertEqual(caught.exception.details["written"], 42)

    def test_write_without_verification_keeps_the_result(self):
        target = self.target()
        result = target.write("app_state.ticks", 42, verify=False)
        self.assertIsNone(result["after"])
        self.assertFalse(result["verified"])

    def test_write_validates_its_arguments(self):
        target = self.target()
        with self.assertRaises(ApiError) as caught:
            target.write("", 1)
        self.assertEqual(caught.exception.code, "invalid_path")
        with self.assertRaises(ApiError) as caught:
            target.write("app_state.ticks", 1, verify="yes")
        self.assertEqual(caught.exception.code, "invalid_verify")

    def test_write_reports_a_refused_command(self):
        target = self.target()
        self.memory = {"app_delay": self.integer}
        with self.assertRaises(ApiError) as caught:
            target.write("app_delay", 100)
        self.assertEqual(caught.exception.code, "command_failed")
        self.assertEqual(caught.exception.details["effect"], "none")

    def test_set_value_is_the_022_alias(self):
        target = self.target()
        self.integer._plain = 5
        self.assertIsNone(target.set_value("app_state.ticks", 5))
        self.assertEqual(target.report["mutations"][0]["after"], 5)


if __name__ == "__main__":
    unittest.main()
