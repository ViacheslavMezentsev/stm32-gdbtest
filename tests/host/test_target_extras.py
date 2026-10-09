"""check with matchers, tables and truth; symbols, raw memory, frame variables and point control."""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import ApiError, CheckFailed, matches, near, one_of, within
from stm32_gdbtest.values import type_constant
from stm32_gdbtest.configuration import DEFAULTS, MEMORY_LIMIT, Configuration, freeze


class FakeError(Exception):
    pass


class FakeBreakpoint:
    counter = 200

    def __init__(self, location, type=None, temporary=False):
        FakeBreakpoint.counter += 1
        self.number = FakeBreakpoint.counter
        self.enabled = True
        self.pending = False
        self.condition = None
        self.ignore_count = 0
        self.locations = [types.SimpleNamespace(address=0x8000100, enabled=True)]
        self._valid = True

    def is_valid(self):
        return self._valid

    def delete(self):
        self._valid = False


class FakeInferior:
    def __init__(self):
        self.memory = bytearray(64)
        self.base = 0x20000100

    def read_memory(self, address, size):
        offset = address - self.base
        if not 0 <= offset <= len(self.memory) - size:
            raise FakeError("cannot access memory")
        return memoryview(bytes(self.memory[offset:offset + size]))

    def write_memory(self, address, data):
        offset = address - self.base
        self.memory[offset:offset + len(data)] = data


class FakeType:
    sizeof = 4

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name


class Symbol:
    def __init__(self, name, value, argument=False, variable=True, function=False, kind="int"):
        self.name = name
        self._value = value
        self.is_argument = argument
        self.is_variable = variable and not argument
        self.is_function = function
        self.type = FakeType(kind)

    def value(self, frame=None):
        return self._value


class Block(list):
    def __init__(self, symbols, superblock=None, function=None, start=0, end=0):
        super().__init__(symbols)
        self.superblock = superblock
        self.function = function
        self.start = start
        self.end = end


def plain(number, optimized=False):
    return types.SimpleNamespace(is_optimized_out=optimized, fetch_lazy=lambda: None, number=number,
                                 address=None)


class Frame:
    def __init__(self, block, name="app_step", older=None):
        self._block = block
        self._name = name
        self._older = older

    def is_valid(self):
        return True

    def block(self):
        if self._block is None:
            raise RuntimeError("Cannot locate block for frame.")
        return self._block

    def name(self):
        return self._name

    def older(self):
        return self._older


class CharType:
    def __init__(self, code, size, element_size=1):
        self.code, self.sizeof, self._element = code, size, element_size

    def strip_typedefs(self):
        return self

    def target(self):
        return types.SimpleNamespace(sizeof=self._element, strip_typedefs=lambda: types.SimpleNamespace(
            sizeof=self._element))


class TextValue:
    """A char array in target memory, a literal of the expression, or a char pointer."""

    def __init__(self, kind, address=None, items=b"", pointer=0):
        self.type, self.address, self._items, self._pointer = kind, address, items, pointer
        self.is_optimized_out = False

    def __getitem__(self, index):
        return self._items[index]

    def cast(self, kind):
        return self._pointer

    def __int__(self):
        return self._pointer


class ExtrasTests(unittest.TestCase):
    def setUp(self):
        self.inferior = FakeInferior()
        self.globals = {}
        self.executed = []
        function_block = Block([Symbol("state", plain(0x20000010), argument=True),
                                Symbol("mode", plain(1), argument=True),
                                Symbol("result", plain(5)),
                                Symbol("scratch", plain(0, optimized=True))], function="app_step")
        inner = Block([Symbol("result", plain(9)), Symbol("index", plain(2))], superblock=function_block)
        self.frame = Frame(inner, older=Frame(None, name="main"))

        def execute(command, to_string=False):
            self.executed.append(command)
            if command.startswith("info symbol"):
                return "app_state in section .bss\n"
            return ""

        self.gdb = types.SimpleNamespace(
            error=FakeError, MemoryError=FakeError,
            Breakpoint=FakeBreakpoint, BP_HARDWARE_BREAKPOINT=1,
            parse_and_eval=lambda expression: types.SimpleNamespace(
                is_optimized_out=False, fetch_lazy=lambda: None, __int__=lambda self: 0),
            execute=execute,
            selected_inferior=lambda: self.inferior,
            newest_frame=lambda: self.frame,
            lookup_global_symbol=lambda name: self.globals.get(name),
            lookup_static_symbol=lambda name: None,
            block_for_pc=lambda pc: Block([], function="app_step", start=0x8000100, end=0x8000140),
            events=types.SimpleNamespace(stop=Mock()),
        )

    def target(self, limit=2):
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
        self.module = module
        profile = {"breakpoint_limit": limit, "fault_handlers": [], "flash_start": 0x08000000,
                   "flash_size": 0x10000}
        configuration = Configuration(freeze(dict(target=profile, image=None,
                                                  api=dict(schema=1, records=dict(DEFAULTS)))),
                                      freeze(dict(target=None, api=None, image=None)), None, {})
        target = module.Target({"checks": []}, profile, configuration)
        patcher = patch.object(module.values, "value_to_plain", lambda value, path, gdb=None: value.number)
        patcher.start()
        self.addCleanup(patcher.stop)
        return target

    # check: matchers, truth and tables.
    def test_matchers_report_value_and_bounds(self):
        target = self.target()
        target.check("vdda", 3300, within(2900, 3600))
        target.check("temperature", 24.6, near(25, 0.5))
        target.check("mode", 1, one_of(0, 1))
        checks = target.report["checks"]
        self.assertEqual(checks[0], dict(name="vdda", actual=3300, expected=dict(low=2900, high=3600),
                                         passed=True, kind="range"))
        self.assertEqual(checks[1]["expected"], dict(value=25, tolerance=0.5))
        self.assertEqual(checks[2]["expected"], {"in": [0, 1]})
        with self.assertRaises(CheckFailed) as caught:
            target.check("vdda", 3700, within(2900, 3600))
        self.assertEqual(caught.exception.details["expected"], dict(low=2900, high=3600))
        for actual, matcher in ((None, within(0, 1)), (26, near(25, 0.5)), (3, one_of(0, 1))):
            with self.subTest(matcher=matcher), self.assertRaises(CheckFailed):
                target.check("mismatch", actual, matcher)

    def test_equality_stays_equality_for_lists(self):
        target = self.target()
        target.check("array", [1, 2], [1, 2])
        with self.assertRaises(CheckFailed):
            target.check("array", [1], [1, 2])

    def test_check_without_expected_tests_truth(self):
        target = self.target()
        target.check("clock enabled", 0x20)
        target.check("flag", True)
        self.assertEqual(target.report["checks"][0], dict(name="clock enabled", actual=0x20, expected=True,
                                                          passed=True, kind="truth"))
        with self.assertRaises(CheckFailed):
            target.check("disabled", 0)

    def test_invalid_matchers_and_arguments_are_operation_errors(self):
        target = self.target()
        for call, code in ((lambda: within(2, 1), "invalid_bounds"),
                           (lambda: within(True, 2), "invalid_bounds"),
                           (lambda: near(1, -1), "invalid_tolerance"),
                           (lambda: one_of(), "invalid_options"),
                           (lambda: target.check("", 1, 1), "invalid_name"),
                           (lambda: target.check("x"), "invalid_arguments"),
                           (lambda: target.check([("a", 1)], 1), "invalid_rows")):
            with self.subTest(code=code), self.assertRaises(ApiError) as caught:
                call()
            self.assertNotIsInstance(caught.exception, CheckFailed)
            self.assertEqual(caught.exception.details["code"], code)
        self.assertEqual(target.report["checks"], [])

    def test_table_evaluates_string_cells_and_stops_at_first_mismatch(self):
        target = self.target()
        target.evaluate = Mock(side_effect=lambda expression: {"app_delay": 500, "DELAY": 500, "ready": 1,
                                                               "app_state.led": 1}[expression])
        rows = [("delay", "app_delay", "DELAY"), ("literal", 3, 3), ("ready", "ready"), ("range", 5, within(1, 9))]
        self.assertEqual(target.check(rows), 4)
        with self.assertRaises(CheckFailed):
            target.check([("led", "app_state.led", 0), ("never", 1, 1)])
        self.assertEqual([check["name"] for check in target.report["checks"]],
                         ["delay", "literal", "ready", "range", "led"])
        for rows in ([], [("only one",)], [("four", 1, 2, 3)]):
            with self.subTest(rows=rows), self.assertRaises(ApiError):
                target.check(rows)

    def test_read_accepts_a_list_of_field_names(self):
        target = self.target()
        target._read_value = Mock(side_effect=lambda expression, path: path)
        self.assertEqual(target.read("app_state", fields=("ticks", "led")),
                         {"ticks": "app_state.ticks", "led": "app_state.led"})

    def test_former_names_are_not_public_methods(self):
        target = self.target()
        for name in ("value", "fields", "set_value", "force_return"):
            with self.subTest(name=name):
                self.assertFalse(hasattr(target, name))

    # Symbols.
    def test_symbol_reports_address_size_type_and_section(self):
        target = self.target()
        self.globals["app_state"] = Symbol("app_state", types.SimpleNamespace(address=0x20000010),
                                           kind="app_state_t")
        result = target.symbol("app_state")
        self.assertEqual(result, dict(operation="symbol", name="app_state", kind="variable",
                                      address=0x20000010, size=4, type="app_state_t", section=".bss"))
        self.globals["app_step"] = Symbol("app_step", types.SimpleNamespace(address=0x8000100),
                                          variable=False, function=True)
        result = target.symbol("app_step")
        self.assertEqual((result["kind"], result["size"]), ("function", 0x40))
        with self.assertRaises(ApiError) as caught:
            target.symbol("missing")
        self.assertEqual(caught.exception.details["code"], "symbol_absent")

    # C strings: evaluate(..., as_type=str).
    def text_target(self, value):
        target = self.target()
        self.gdb.parse_and_eval = lambda expression: value
        self.gdb.lookup_type = lambda name: name
        return target

    def test_char_array_reads_up_to_the_first_zero(self):
        array = type_constant("TYPE_CODE_ARRAY", None)
        self.inferior.memory[0:16] = b"v1.2.0-ci\0garbage"[:16]
        target = self.text_target(TextValue(CharType(array, 16), address=0x20000100))
        self.assertEqual(target.evaluate("app_info.version", as_type=str), "v1.2.0-ci")
        self.assertEqual(target.evaluate("app_info.version", as_type="str"), "v1.2.0-ci")
        self.assertEqual(target.report["evaluations"][-1]["value_type"], "str")
        self.assertNotIn("truncated", target.report["evaluations"][-1])

    def test_literal_and_pointer_strings(self):
        array, pointer = type_constant("TYPE_CODE_ARRAY", None), type_constant("TYPE_CODE_PTR", None)
        target = self.text_target(TextValue(CharType(array, 5), items=b"v1.2\0"))
        self.assertEqual(target.evaluate('"v1.2"', as_type=str), "v1.2")
        self.inferior.memory[0:20] = b"stm32-gdbtest-ci\0\0\0\0"
        target = self.text_target(TextValue(CharType(pointer, 4), pointer=0x20000100))
        self.assertEqual(target.evaluate("app_info.board", as_type=str), "stm32-gdbtest-ci")

    def test_string_refusals_and_truncation(self):
        array, pointer = type_constant("TYPE_CODE_ARRAY", None), type_constant("TYPE_CODE_PTR", None)
        target = self.text_target(TextValue(CharType(pointer, 4), pointer=0))
        with self.assertRaises(ApiError) as caught:
            target.evaluate("app_info.board", as_type=str)
        self.assertEqual(caught.exception.details["code"], "null_pointer")
        target = self.text_target(TextValue(CharType(array, 8, element_size=4), address=0x20000100))
        with self.assertRaises(ApiError) as caught:
            target.evaluate("words", as_type=str)
        self.assertEqual(caught.exception.details["code"], "unsupported_type")
        # A pointer string without a zero before the end of readable memory is returned truncated.
        self.inferior.memory[:] = b"x" * len(self.inferior.memory)
        target = self.text_target(TextValue(CharType(pointer, 4), pointer=0x20000100))
        self.assertEqual(target.evaluate("p", as_type=str), "x" * 64)
        self.assertTrue(target.report["evaluations"][-1]["truncated"])
        self.inferior.memory[0:3] = b"\xff\xfeA"
        self.inferior.memory[3] = 0
        self.assertEqual(target.evaluate("p", as_type=str), "\ufffd\ufffdA")

    def test_matches_searches_a_python_pattern(self):
        target = self.target()
        target.check("version", "v1.2.0-ci", matches(r"^v1\."))
        self.assertEqual(target.report["checks"][-1]["expected"], {"matches": r"^v1\."})
        self.assertEqual(target.report["checks"][-1]["kind"], "matches")
        with self.assertRaises(CheckFailed):
            target.check("version", "v2.0", matches(r"^v1\."))
        with self.assertRaises(CheckFailed):
            target.check("not text", 12, matches("1"))
        for pattern in ("(", 5):
            with self.subTest(pattern=pattern), self.assertRaises(ApiError) as caught:
                matches(pattern)
            self.assertEqual(caught.exception.details["code"], "invalid_pattern")

    def test_table_names_the_row_when_a_string_cell_is_not_an_expression(self):
        target = self.target()
        def refuse(expression):
            raise FakeError(f'No symbol "{expression}" in current context.')
        self.gdb.parse_and_eval = refuse
        with self.assertRaises(ApiError) as caught:
            target.check([("case id", "HW_CI_PROFILE", "HW_CI_PROFILE")])
        self.assertEqual((caught.exception.details["row"], caught.exception.details["cell"]), ("case id", "actual"))
        self.assertIn("compare Python values with check(name, actual, expected)", str(caught.exception))

    # Expected refusals.
    def test_refused_records_one_check_and_suppresses_the_error(self):
        target = self.target()
        with target.refused("limit_exceeded", effect="none") as refusal:
            target._fail("breakpoint", "validation", "none", "limit_exceeded", "budget", limit=2)
        self.assertEqual(refusal.details["limit"], 2)
        entry = target.report["checks"][-1]
        self.assertEqual(entry, dict(name="refused: limit_exceeded", actual=dict(code="limit_exceeded", effect="none"),
                                     expected=dict(code="limit_exceeded", effect="none"), passed=True, kind="refused"))

    def test_refused_fails_on_success_and_on_another_code(self):
        target = self.target()
        with self.assertRaises(CheckFailed):
            with target.refused("invalid_path", name="must be refused"):
                pass
        self.assertEqual((target.report["checks"][-1]["name"], target.report["checks"][-1]["actual"]),
                         ("must be refused", None))
        with self.assertRaises(CheckFailed):
            with target.refused("invalid_path"):
                target._fail("watch", "validation", "none", "not_addressable", "no address")
        self.assertEqual(target.report["checks"][-1]["actual"], dict(code="not_addressable"))

    def test_refused_passes_other_exceptions_through(self):
        target = self.target()
        with self.assertRaises(CheckFailed):
            with target.refused("invalid_path"):
                target.check("inner mismatch", 1, 2)
        with self.assertRaises(KeyError):
            with target.refused("invalid_path"):
                raise KeyError("x")
        with self.assertRaises(ApiError):
            target.refused("")

    # Writes: rows and expressions.
    def write_target(self):
        target = self.target()
        state = {"x": 5, "ADC1->CR": 0}
        def read(expression, path):
            return eval(expression.replace("ADC1->CR", "ADC1_CR").replace("ADC_CR_ADSTART", "4"),
                        {}, {"x": state["x"], "ADC1_CR": state["ADC1->CR"]})
        target._read_value = read
        target._verify_scope = lambda path: (path == "x", 0x20000000 if path == "x" else 0x40012408)
        def write_expression(path, literal):
            state[path] = read(literal, literal)
        target._write_expression = write_expression
        return target, state

    def test_write_rows_in_order_with_read_modify_write(self):
        target, state = self.write_target()
        results = target.write([("ADC1->CR", "ADC1->CR | ADC_CR_ADSTART"), ("x", "x + 1")])
        self.assertEqual(state, {"x": 6, "ADC1->CR": 4})
        self.assertEqual([r["path"] for r in results], ["ADC1->CR", "x"])
        self.assertTrue(results[1]["verified"])
        self.assertEqual([m["expression"] for m in target.report["mutations"]], ["ADC1->CR", "x"])

    def test_write_rows_and_values_are_validated(self):
        target, state = self.write_target()
        for call, code in ((lambda: target.write([]), "invalid_rows"),
                           (lambda: target.write([("x",)]), "invalid_rows"),
                           (lambda: target.write([("x", 1)], 2), "invalid_rows"),
                           (lambda: target.write("x"), "unsupported_value"),
                           (lambda: target.write("x", "y = 1"), "unsupported_value"),
                           (lambda: target.write("x", "x <<= 1"), "unsupported_value"),
                           (lambda: target.write("x", "x; y"), "unsupported_value")):
            with self.subTest(code=code), self.assertRaises(ApiError) as caught:
                call()
            self.assertEqual(caught.exception.details["code"], code)
        self.assertEqual(state["x"], 5)

    # Raw memory: the type of the second argument decides.
    def test_memory_reads_with_a_size_and_writes_bytes(self):
        target = self.target()
        self.inferior.memory[0:4] = b"\x01\x02\x03\x04"
        self.assertEqual(target.memory(0x20000100, 4), b"\x01\x02\x03\x04")
        result = target.memory(0x20000104, b"\xAA\xBB")
        self.assertEqual(result, dict(operation="memory", address=0x20000104, size=2, verified=True))
        self.assertEqual(bytes(self.inferior.memory[4:6]), b"\xAA\xBB")
        mutation = target.report["mutations"][0]
        self.assertEqual((mutation["before"], mutation["after"]), ("0000", "aabb"))
        self.assertEqual(target.memory(0x20000108, bytearray(b"\x05"), verify=False)["verified"], False)
        self.assertEqual(target.memory(0x2000010A, memoryview(b"\x06"))["size"], 1)

    def test_memory_refuses_peripherals_and_bad_arguments(self):
        target = self.target()
        cases = ((lambda: target.memory(0x40021000, 4), "outside_window"),
                 (lambda: target.memory(0x08000000, 0), "invalid_block"),
                 (lambda: target.memory(0x20000100, MEMORY_LIMIT + 1), "invalid_block"),
                 (lambda: target.memory(0x08000000, b"\x00"), "outside_window"),
                 (lambda: target.memory(0x20000100, "text"), "invalid_block"),
                 (lambda: target.memory(0x20000100, [1, 2]), "invalid_block"),
                 (lambda: target.memory(0x20000100, True), "invalid_block"),
                 (lambda: target.memory(-1, 4), "invalid_block"),
                 (lambda: target.memory(0x20000100, 4, verify=False), "invalid_verify"),
                 (lambda: target.memory(0x20000000, 4), "read_failed"))
        for call, code in cases:
            with self.subTest(code=code), self.assertRaises(ApiError) as caught:
                call()
            self.assertEqual(caught.exception.details["code"], code)

    def test_memory_reads_the_profile_flash(self):
        target = self.target()
        with self.assertRaises(ApiError) as caught:
            target.memory(0x0800FFFE, 4)
        self.assertEqual(caught.exception.details["code"], "outside_window")
        with self.assertRaises(ApiError) as caught:
            target.memory(0x08000000, 4)
        self.assertEqual(caught.exception.details["code"], "read_failed")

    # Frame variables.
    def test_locals_and_arguments(self):
        target = self.target()
        self.assertEqual(target.arguments(), dict(operation="arguments", function="app_step",
                                                  values=dict(state=0x20000010, mode=1), unavailable=[]))
        result = target.locals()
        self.assertEqual(result["values"], dict(result=9, index=2))
        self.assertEqual(result["unavailable"], ["scratch"])
        with self.assertRaises(ApiError) as caught:
            target.locals(1)
        self.assertEqual(caught.exception.details["code"], "no_debug_info")
        with self.assertRaises(ApiError) as caught:
            target.arguments(5)
        self.assertEqual(caught.exception.details["code"], "no_frame")

    # Point control.
    def test_disable_frees_the_budget_and_enable_respects_it(self):
        target = self.target(limit=2)
        first = target.breakpoint("app_loop")
        second = target.breakpoint("app_step")
        first.hit_count = 3
        self.assertIs(first.disable(), first)
        self.assertFalse(first.active)
        self.assertFalse(first.enabled)
        third = target.breakpoint("board_tick")
        with self.assertRaises(ApiError) as caught:
            first.enable()
        self.assertEqual(caught.exception.details["code"], "limit_exceeded")
        third.remove()
        first.enable()
        self.assertTrue(first.active)
        self.assertEqual(first.hit_count, 3)
        second.remove()
        with self.assertRaises(ApiError) as caught:
            second.enable()
        self.assertEqual(caught.exception.details["code"], "point_removed")

    def test_addresses_are_integers_of_the_gdb_locations(self):
        target = self.target()
        point = target.breakpoint("app_step")
        self.assertEqual(point.addresses, [0x8000100])
        self.assertIs(type(point.addresses[0]), int)
        point.remove()
        self.assertEqual(point.addresses, [])

    def test_condition_is_writable(self):
        target = self.target()
        point = target.breakpoint("app_step", condition="mode == 1")
        point.condition = "mode == 0"
        self.assertEqual((point.condition, point._native.condition), ("mode == 0", "mode == 0"))
        self.assertIs(target.breakpoint("app_step", condition="mode == 0"), point)
        point.condition = None
        self.assertIsNone(point._native.condition)
        with self.assertRaises(ApiError):
            point.condition = ""


if __name__ == "__main__":
    unittest.main()
