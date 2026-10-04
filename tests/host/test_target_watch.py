"""Watch points: addressable objects, budget, refusals and stop classification."""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import ApiError
from stm32_gdbtest.configuration import DEFAULTS, Configuration, freeze

TYPE_CODE_INT, TYPE_CODE_STRUCT, TYPE_CODE_PTR, TYPE_CODE_ARRAY = 8, 4, 1, 5
BP_WATCHPOINT = 6
WP_WRITE = 0


class FakeError(Exception):
    pass


class FakeType:
    def __init__(self, code=TYPE_CODE_INT, size=4, name="uint32_t", target=None):
        self.code = code
        self.sizeof = size
        self.name = name
        self._target = target

    def target(self):
        return self._target or self

    def unqualified(self):
        return self


class FakeNative:
    counter = 300

    def __init__(self, location, type=None, temporary=False):
        FakeNative.counter += 1
        self.number = FakeNative.counter
        self.location = None
        self.expression = location
        self.enabled = True
        self.pending = False
        self.type = type
        self._valid = True

    def is_valid(self):
        return self._valid

    def delete(self):
        self._valid = False


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        self.frame = types.SimpleNamespace(is_valid=lambda: True, name=lambda: "app_loop",
                                           pc=lambda: 0x8000100, older=lambda: None)

        def breakpoint(location, type=None, temporary=False):
            native = FakeNative(location, type, temporary)
            self.created.append(native)
            return native

        def parse(expression):
            if expression == "app_state.ticks":
                return types.SimpleNamespace(type=FakeType(), address=0x20000008,
                                             is_optimized_out=False,
                                             fetch_lazy=lambda: None, __int__=lambda self: 7)
            if expression == "app_state":
                return types.SimpleNamespace(type=FakeType(TYPE_CODE_STRUCT, 12, "app_state_t"),
                                             address=0x20000000, is_optimized_out=False)
            if expression == "board_handle":
                return types.SimpleNamespace(type=FakeType(TYPE_CODE_PTR, 4, "board_handle_t *"),
                                             address=0x20000040,
                                             is_optimized_out=False)
            if expression == "odd":
                return types.SimpleNamespace(type=FakeType(TYPE_CODE_INT, 4), address=0x2000000A,
                                             is_optimized_out=False)
            if expression == "no_address":
                return types.SimpleNamespace(type=FakeType(), address=None, is_optimized_out=False)
            if expression == "unknown_thing":
                raise FakeError("no symbol")
            return types.SimpleNamespace(type=FakeType(), address=0x20000010, is_optimized_out=False)

        self.gdb = types.SimpleNamespace(
            error=FakeError,
            Breakpoint=breakpoint,
            BP_HARDWARE_BREAKPOINT=1,
            # The core reads these codes from the loaded module.
            TYPE_CODE_INT=TYPE_CODE_INT,
            TYPE_CODE_STRUCT=TYPE_CODE_STRUCT,
            TYPE_CODE_PTR=TYPE_CODE_PTR,
            TYPE_CODE_ARRAY=TYPE_CODE_ARRAY,
            TYPE_CODE_VOID=10,
            TYPE_CODE_FLT=12,
            TYPE_CODE_BOOL=11,
            TYPE_CODE_ENUM=3,
            TYPE_CODE_UNION=6,
            TYPE_CODE_REF=16,
            TYPE_CODE_RVALUE_REF=17,
            TYPE_CODE_CHAR=2,
            BP_WATCHPOINT=BP_WATCHPOINT,
            WP_WRITE=WP_WRITE,
            parse_and_eval=parse,
            newest_frame=lambda: self.frame,
            events=types.SimpleNamespace(stop=Mock()),
        )

    def target(self, limit=4):
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
        return module.Target({"checks": []}, {"breakpoint_limit": limit, "fault_handlers": []},
                             configuration)

    def test_watch_creates_a_write_watchpoint_by_address(self):
        target = self.target()
        point = target.watch("app_state.ticks")
        self.assertEqual(self.created[-1].expression, "*0x20000008")
        self.assertEqual(self.created[-1].type, BP_WATCHPOINT)
        self.assertTrue(point.watch)
        self.assertTrue(point.active)
        self.assertEqual(point.location, "app_state.ticks")
        self.assertIn(point, target.owned)

    def test_watch_refuses_a_wide_structure(self):
        target = self.target()
        # A hardware watch unit covers at most eight bytes, so a twelve byte object is refused.
        with self.assertRaises(ApiError) as caught:
            target.watch("app_state")
        self.assertEqual(caught.exception.code, "unsupported_width")
        self.assertEqual(caught.exception.details["size"], 12)

    def test_watch_refuses_object_kinds_and_widths(self):
        target = self.target()
        for path, code in (("board_handle", "unsupported_object"), ("unknown_thing", "invalid_path"),
                           ("no_address", "not_addressable")):
            with self.subTest(path=path):
                with self.assertRaises(ApiError) as caught:
                    target.watch(path)
                self.assertEqual(caught.exception.code, code, path)
        with self.assertRaises(ApiError) as caught:
            target.watch("odd")
        self.assertEqual(caught.exception.code, "unsupported_width")

    def test_watch_rejects_an_invalid_path_argument(self):
        target = self.target()
        for path in ("", "   ", 7, None):
            with self.subTest(path=path):
                with self.assertRaises(ApiError) as caught:
                    target.watch(path)
                self.assertEqual(caught.exception.code, "invalid_path")
        self.assertEqual(self.created, [])

    def test_watch_shares_the_budget_with_breakpoints(self):
        target = self.target(limit=2)
        target.watch("app_state.ticks")
        target.breakpoint("app_loop")
        # Two points are active and the budget is two, so the next watch is refused.
        with self.assertRaises(ApiError) as caught:
            target.watch("app_state.ticks")
        self.assertEqual(caught.exception.code, "limit_exceeded")
        self.assertEqual(caught.exception.details["limit"], 2)

    def test_watch_reports_a_backend_without_watchpoints(self):
        target = self.target()

        def refusing(location, type=None, temporary=False):
            raise FakeError("Hardware watchpoint not supported")

        self.gdb.Breakpoint = refusing
        with self.assertRaises(ApiError) as caught:
            target.watch("app_state.ticks")
        self.assertEqual(caught.exception.code, "command_failed")
        self.assertEqual(caught.exception.details["effect"], "none")
        self.assertIsInstance(caught.exception.__cause__, FakeError)

    def test_watch_stops_are_classified_as_watchpoints(self):
        target = self.target()
        point = target.watch("app_state.ticks")
        target.stops = [{"type": "BreakpointEvent", "breakpoints": [point.id],
                         "signal": None, "native_reason": "watchpoint-trigger"}]
        self.assertEqual(target._stop_kind(target.stops[0]), "watchpoint")
        target.stops = [{"type": "BreakpointEvent", "breakpoints": [point.id],
                         "signal": None, "native_reason": "breakpoint-hit"}]
        self.assertEqual(target._stop_kind(target.stops[0]), "watchpoint")
        # J-Link reports a watch point stop as a breakpoint event without any reason.
        target.stops = [{"type": "BreakpointEvent", "breakpoints": [point.id],
                         "signal": None, "native_reason": None}]
        self.assertEqual(target._stop_kind(target.stops[0]), "watchpoint")
        regular = target.breakpoint("app_loop")
        target.stops = [{"type": "BreakpointEvent", "breakpoints": [regular.id],
                         "signal": None, "native_reason": None}]
        self.assertEqual(target._stop_kind(target.stops[0]), "breakpoint")


if __name__ == "__main__":
    unittest.main()
