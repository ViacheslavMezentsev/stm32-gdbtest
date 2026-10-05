"""Navigation, points and their diagnostics, with only the GDB surface substituted.

The fake GDB keeps native breakpoints with numbers, dispatches one stop event per executed command
and exposes a frame, which is what the implementation observes.
"""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import ApiError, CheckFailed
from stm32_gdbtest.configuration import Configuration, DEFAULTS, freeze


class FakeError(Exception):
    pass


class FakeBreakpoint:
    counter = 100

    def __init__(self, location, type=None, temporary=False):
        FakeBreakpoint.counter += 1
        self.number = FakeBreakpoint.counter
        self.location = location
        self.temporary = temporary
        self.enabled = True
        self.pending = False
        self.condition = None
        self.ignore_count = 0
        self.locations = [0x8000100]
        self._valid = True

    def is_valid(self):
        return self._valid

    def delete(self):
        self._valid = False


class FakeBreakpointEvent:
    def __init__(self, breakpoints, reason=None):
        self.breakpoints = breakpoints
        self.details = {"reason": reason} if reason else {}
        self.stop_signal = None


class FakeFrame:
    def __init__(self, name="app_loop", pc=0x8000100, return_value=None):
        self._name = name
        self._pc = pc
        self.return_value = return_value

    def name(self):
        return self._name

    def pc(self):
        return self._pc


class FakeThread:
    def is_stopped(self):
        return True


class FakeValue:
    """A scalar value with the two attributes the implementation inspects."""

    def __init__(self, plain=1, optimized=False):
        self._plain = plain
        self.is_optimized_out = optimized

    def fetch_lazy(self):
        return None

    def __int__(self):
        return int(self._plain)

    def __bool__(self):
        return bool(self._plain)


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.integer = FakeValue(1)
        self.frame = FakeFrame()
        self.listeners = []
        self.executed = []
        self.raw_events = []

        def execute(command, **options):
            self.executed.append(command)
            # Every command consumes at most one queued stop event, as a real continue would.
            if self.raw_events:
                event = self.raw_events.pop(0)
                for listener in list(self.listeners):
                    listener(event)
            return ""

        self.gdb = types.SimpleNamespace(
            error=FakeError,
            Breakpoint=FakeBreakpoint,
            BP_HARDWARE_BREAKPOINT=1,
            parse_and_eval=lambda expression: self.integer,
            execute=execute,
            newest_frame=lambda: self.frame,
            selected_thread=lambda: FakeThread(),
            events=types.SimpleNamespace(
                stop=types.SimpleNamespace(
                    connect=lambda listener: self.listeners.append(listener),
                    disconnect=lambda listener: self.listeners.remove(listener))),
        )

    def target(self, profile=None):
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
        settings = {"breakpoint_limit": 4, "fault_handlers": ["HardFault_Handler"]}
        if profile:
            settings.update(profile)
        return module.Target({"checks": [], "stops": []}, settings, configuration)

    def stop(self, *numbers, reason="breakpoint", signal=None):
        event = FakeBreakpointEvent([types.SimpleNamespace(number=number, type=1)
                                     for number in numbers], reason)
        event.stop_signal = signal
        self.raw_events = [event]
    def test_clear_removes_every_point(self):
        # remove() rewrites the ownership list; clear() must not skip every second point.
        target = self.target({"breakpoint_limit": 6})
        points = [target.breakpoint(name) for name in ("a", "b", "c", "d")]
        target.clear()
        self.assertEqual([p.location for p in points if p._native.is_valid()], [])
        self.assertEqual(target.owned, [])

    def test_reach_keeps_a_point_set_by_the_scenario(self):
        target = self.target()
        persistent = target.breakpoint("app_loop")
        self.stop(persistent.id, 999)

        def execute(command, **options):
            self.executed.append(command)
            temporary = [p for p in target.owned if p.temporary][0]
            event = FakeBreakpointEvent([types.SimpleNamespace(number=n, type=1)
                                         for n in (persistent.id, temporary.id)], "breakpoint")
            for listener in list(self.listeners):
                listener(event)
            return ""

        self.gdb.execute = execute
        target.reach("app_loop")
        self.assertTrue(persistent.active)
        self.assertEqual([p.id for p in target.owned], [persistent.id])

    def test_a_new_condition_is_never_dropped_by_reuse(self):
        target = self.target()
        plain = target.breakpoint("app_loop")
        conditioned = target.breakpoint("app_loop", condition="x == 3")
        self.assertIsNot(plain, conditioned)
        self.assertEqual(conditioned._native.condition, "x == 3")
        self.assertIs(target.breakpoint("app_loop", condition="x == 3"), conditioned)
        temporary = target.breakpoint("app_loop", temporary=True)
        self.assertIsNot(temporary, plain)

    def test_when_is_the_02x_name_of_condition(self):
        target = self.target()
        point = target.breakpoint("app_loop", True, when="x == 3")
        self.assertTrue(point.temporary)
        self.assertEqual(point._native.condition, "x == 3")
        with self.assertRaises(ApiError) as caught:
            target.breakpoint("app_step", condition="a", when="b")
        self.assertEqual(caught.exception.code, "conflicting_condition")
        self.assertEqual(caught.exception.details["stage"], "validation")

    def test_point_keeps_the_gdb_breakpoint_spelling(self):
        target = self.target()
        point = target.breakpoint("app_loop")
        self.assertTrue(point.is_valid())
        point.delete()
        self.assertFalse(point.is_valid())
        self.assertEqual(target.owned, [])

    def test_breakpoint_returns_a_reusable_point(self):
        target = self.target()
        first = target.breakpoint("app_loop")
        second = target.breakpoint("app_loop")
        self.assertIs(first, second)
        self.assertEqual(first.id, second.id)
        self.assertTrue(first.active)
        first.remove()
        self.assertFalse(first.active)
        self.assertIsNotNone(target.breakpoint("app_loop"))

    def test_point_context_manager_removes_the_point(self):
        target = self.target()
        with target.breakpoint("board_led_toggle") as point:
            self.assertTrue(point.active)
        self.assertFalse(point.active)

    def test_breakpoint_conditions_and_budget(self):
        target = self.target()
        point = target.breakpoint("app_loop", condition="app_state.ticks > 2", ignore_count=3)
        self.assertEqual(point._native.condition, "app_state.ticks > 2")
        self.assertEqual(point._native.ignore_count, 3)
        for index in range(3):
            target.breakpoint(f"location_{index}")
        with self.assertRaises(ApiError) as caught:
            target.breakpoint("app_step")
        self.assertEqual(caught.exception.code, "limit_exceeded")
        self.assertEqual(caught.exception.details["limit"], 4)
        self.assertEqual(len(target.owned), 4)

    def test_breakpoint_rejects_invalid_input_and_absent_symbols(self):
        target = self.target()
        with self.assertRaises(ApiError) as caught:
            target.breakpoint("")
        self.assertEqual(caught.exception.code, "invalid_location")

        def pending_breakpoint(location, type=None, temporary=False):
            point = FakeBreakpoint(location, type, temporary)
            point.pending = True
            return point

        self.gdb.Breakpoint = pending_breakpoint
        with self.assertRaises(ApiError) as caught:
            target.breakpoint("missing_symbol")
        self.assertEqual(caught.exception.code, "symbol_absent")
        self.assertEqual(target.owned, [])

    def test_reach_reports_the_point_and_counts_the_hit(self):
        target = self.target()
        self.frame = FakeFrame(name="app_loop", pc=0x8000200)
        original = target.breakpoint

        def spy(location, **options):
            point = original(location, **options)
            self.stop(point.id)
            return point

        target.breakpoint = spy
        result = target.reach("app_loop")
        self.assertEqual(result["outcome"], "reached")
        self.assertEqual(result["location"], "app_loop")
        self.assertEqual(result["addresses"], [0x8000100])
        self.assertEqual(result["stop"]["kind"], "breakpoint")
        self.assertEqual(result["stop"]["function"], "app_loop")
        self.assertEqual(len(target.report["checks"]), 2)

    def test_reach_fails_when_another_point_stopped(self):
        target = self.target()
        self.stop(999)
        with self.assertRaises(ApiError) as caught:
            target.reach("app_loop")
        self.assertEqual(caught.exception.code, "unknown_stop")
        self.assertEqual(caught.exception.details["stop"]["breakpoints"], [999])
        self.assertEqual(target.report["checks"], [])

    def test_resume_returns_the_stop(self):
        target = self.target()
        self.stop(reason="end-stepping-range")
        result = target.resume()
        self.assertEqual(result["outcome"], "stopped")
        self.assertEqual(result["stop"]["kind"], "step")
        self.assertEqual(self.executed[-1], "continue")

    def test_resume_classifies_a_fault_guard(self):
        target = self.target()
        guard = target.breakpoint("HardFault_Handler")
        self.stop(guard.id)
        with self.assertRaises(ApiError) as caught:
            target.resume()
        self.assertEqual(caught.exception.code, "fault_stop")

    def test_step_uses_the_requested_command(self):
        target = self.target()
        self.raw_events = [FakeBreakpointEvent([], "end-stepping-range"),
                           FakeBreakpointEvent([], "end-stepping-range")]
        result = target.step(2, unit="instruction", mode="over")
        self.assertEqual(result["outcome"], "completed")
        self.assertEqual(result["completed"], 2)
        self.assertEqual(self.executed[-2:], ["nexti", "nexti"])

    def test_step_is_interrupted_by_a_breakpoint(self):
        target = self.target()
        point = target.breakpoint("app_loop")
        self.stop(point.id)
        result = target.step(3)
        self.assertEqual(result["outcome"], "interrupted")
        self.assertEqual(result["completed"], 0)
        self.assertEqual(result["requested"], 3)

    def test_step_rejects_invalid_arguments(self):
        target = self.target()
        with self.assertRaises(ApiError) as caught:
            target.step(0)
        self.assertEqual(caught.exception.code, "invalid_count")
        with self.assertRaises(ApiError) as caught:
            target.step(1, unit="source", mode="sideways")
        self.assertEqual(caught.exception.code, "invalid_mode")

    def test_step_reports_an_unconfirmed_completion(self):
        target = self.target()
        self.stop(reason="something-else")
        with self.assertRaises(ApiError) as caught:
            target.step(1)
        self.assertEqual(caught.exception.code, "completion_unconfirmed")
        self.assertEqual(caught.exception.details["completed"], 0)
        self.assertEqual(caught.exception.details["stop"]["kind"], "other")

    def test_until_reaches_a_location_or_ends_the_line(self):
        target = self.target()
        self.stop(reason="location-reached")
        reached = target.until("app_loop")
        self.assertEqual((reached["outcome"], reached["location"]), ("reached", "app_loop"))
        self.assertEqual(self.executed[-1], "until app_loop")
        self.stop(reason="end-stepping-range")
        completed = target.until()
        self.assertEqual(completed["outcome"], "completed")
        self.assertEqual(self.executed[-1], "until")

    def test_until_rejects_an_empty_location(self):
        target = self.target()
        with self.assertRaises(ApiError) as caught:
            target.until("  ")
        self.assertEqual(caught.exception.code, "invalid_location")

    @staticmethod
    def returned(plain):
        """A returned scalar as GDB stores it in the history: an int-typed value."""
        value = FakeValue(plain)
        value.type = types.SimpleNamespace(code=8)
        return value

    def history(self, *values):
        """GDB value history: `finish` appends the returned value, as "Value returned is $N"."""
        stored = []
        self.gdb.history_count = lambda: len(stored)
        self.gdb.history = lambda index: stored[-1 - index]
        original = self.gdb.execute

        def execute(command, **options):
            result = original(command, **options)
            if command == "finish" and values:
                stored.append(values[0])
            return result

        self.gdb.execute = execute
        return stored

    def test_finish_reports_the_returned_value_from_the_history(self):
        target = self.target()
        self.history(self.returned(42))
        self.frame = FakeFrame(name="app_step")
        self.stop(reason="function-finished")
        result = target.finish()
        self.assertEqual(result["outcome"], "completed")
        self.assertEqual(result["returned_from"], "app_step")
        self.assertEqual(result["return_value"], 42)
        self.assertEqual(result["return_state"], "available")
        self.assertEqual(result["stop"]["evidence"], "native")
        self.assertEqual(self.executed[-1], "finish")

    def test_finish_without_a_history_entry_is_unavailable(self):
        target = self.target()
        self.history()
        self.stop(reason="function-finished")
        result = target.finish()
        self.assertIsNone(result["return_value"])
        self.assertEqual(result["return_state"], "unavailable")

    def test_finish_of_a_void_function_is_void_not_unavailable(self):
        target = self.target()
        self.history()
        void = types.SimpleNamespace(code=10, sizeof=1, name="void")
        self.integer.type = types.SimpleNamespace(target=lambda: void)
        self.stop(reason="function-finished")
        result = target.finish()
        self.assertIsNone(result["return_value"])
        self.assertEqual(result["return_state"], "void")

    def test_finish_on_gdb14_is_inferred_and_warned_once(self):
        # GDB 14 attaches no details: the changed frame proves the return, the stop says so.
        target = self.target()
        self.history(self.returned(7))
        self.frame = FakeFrame(name="app_step", pc=0x8000100)
        caller = FakeFrame(name="app_receiver_step", pc=0x8000200)
        original = self.gdb.execute

        def execute(command, **options):
            result = original(command, **options)
            self.frame = caller
            return result

        self.gdb.execute = execute
        self.raw_events = [FakeBreakpointEvent([], None)]
        result = target.finish()
        self.assertEqual(result["stop"]["kind"], "function_return")
        self.assertTrue(result["stop"]["inferred"])
        self.assertEqual(result["stop"]["evidence"], "inferred")
        self.assertEqual(result["function"], "app_receiver_step")
        self.assertEqual(result["return_value"], 7)
        self.assertEqual([w["code"] for w in target.report["warnings"]], ["inferred_stop"])

    def test_step_on_gdb14_counts_a_moved_pc_as_a_step(self):
        target = self.target()
        frames = iter([FakeFrame(name="app_receiver_step", pc=0x8000300)] * 4)
        original = self.gdb.execute

        def execute(command, **options):
            result = original(command, **options)
            self.frame = next(frames)
            return result

        self.gdb.execute = execute
        self.raw_events = [FakeBreakpointEvent([], None)]
        result = target.step(1, unit="source", mode="into")
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["stop"]["kind"], "step")
        self.assertTrue(result["stop"]["inferred"])

    def test_until_on_gdb14_leaving_the_line_is_a_step_even_in_the_caller(self):
        # GDB 15+ report end-stepping-range when until leaves the function; GDB 14 must agree.
        target = self.target()
        self.frame = FakeFrame(name="board_led_toggle", pc=0x8000100)
        original = self.gdb.execute

        def execute(command, **options):
            result = original(command, **options)
            self.frame = FakeFrame(name="app_loop", pc=0x8000600)
            return result

        self.gdb.execute = execute
        self.raw_events = [FakeBreakpointEvent([], None)]
        result = target.until()
        self.assertEqual(result["outcome"], "completed")
        self.assertEqual(result["stop"]["kind"], "step")
        self.assertTrue(result["stop"]["inferred"])

    def test_until_reports_reached_only_at_the_target_address(self):
        target = self.target()
        self.gdb.decode_line = lambda location: ("", [types.SimpleNamespace(pc=0x8000400)])
        frames = {"next": FakeFrame(name="app_loop", pc=0x8000400)}
        original = self.gdb.execute

        def execute(command, **options):
            result = original(command, **options)
            self.frame = frames["next"]
            return result

        self.gdb.execute = execute
        self.stop(reason="location-reached")
        reached = target.until("app.c:20")
        self.assertEqual((reached["outcome"], reached["targets"]), ("reached", [0x8000400]))
        # GDB 16 says location-reached also when the frame returned first: the address decides.
        self.frame = FakeFrame(name="app_step", pc=0x8000100)
        frames["next"] = FakeFrame(name="app_loop", pc=0x8000500)
        self.stop(reason="location-reached")
        exited = target.until("app.c:20")
        self.assertEqual(exited["outcome"], "frame_exited")

    def test_unknown_stop_reason_is_an_error(self):
        target = self.target()
        self.stop(999)
        with self.assertRaises(ApiError) as caught:
            target.resume()
        self.assertEqual(caught.exception.code, "unknown_stop")
        self.assertIn("breakpoints", caught.exception.details["stop"])

    def test_hit_count_grows_with_observed_stops(self):
        target = self.target()
        point = target.breakpoint("app_loop")
        self.stop(point.id)
        target.resume()
        self.stop(point.id)
        target.resume()
        self.assertEqual(point.hit_count, 2)


if __name__ == "__main__":
    unittest.main()
