"""Reset: the command precedence, cache invalidation and refusals."""
import importlib
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import ApiError
from stm32_gdbtest.configuration import DEFAULTS, RESET_COMMAND, Configuration, freeze

TYPE_CODE_INT = 8


class FakeError(Exception):
    pass


class FakeType:
    def __init__(self, name="uint32_t", code=TYPE_CODE_INT, size=4):
        self.name = name
        self.code = code
        self.sizeof = size


class FakeBreakpoint:
    counter = 200

    def __init__(self, location, type=None, temporary=False):
        FakeBreakpoint.counter += 1
        self.number = FakeBreakpoint.counter
        self.location = location
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


class FakeFrame:
    def __init__(self, pc=0x8000100):
        self._pc = pc

    def is_valid(self):
        return True

    def name(self):
        return "main"

    def pc(self):
        return self._pc


class ResetTests(unittest.TestCase):
    def setUp(self):
        self.commands = []
        self.reset_failure = None
        self.frame = FakeFrame()
        self.invalidate_calls = 0

        def execute(command, **options):
            self.commands.append(command)
            if self.reset_failure is not None and command == self.reset_failure:
                raise FakeError("reset refused by the backend")
            return ""

        def invalidate_cached_frames():
            self.invalidate_calls += 1

        self.gdb = types.SimpleNamespace(
            error=FakeError,
            execute=execute,
            Breakpoint=FakeBreakpoint,
            BP_HARDWARE_BREAKPOINT=1,
            invalidate_cached_frames=invalidate_cached_frames,
            newest_frame=lambda: self.frame,
            parse_and_eval=lambda expression: types.SimpleNamespace(
                is_optimized_out=False, fetch_lazy=lambda: None, __int__=lambda self: 0),
            events=types.SimpleNamespace(stop=Mock()),
        )

    def target(self, command=None, profile=None):
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
        api = dict(schema=1, records=dict(DEFAULTS))
        if command is not None:
            api["reset"] = dict(command=command)
        configuration = Configuration(freeze(dict(target={}, image=None, api=api)),
                                      freeze(dict(target=None, api=None, image=None)), None, {})
        settings = {"breakpoint_limit": 4, "fault_handlers": ["HardFault_Handler"]}
        if profile:
            settings.update(profile)
        report = {"checks": [], "resets": []}
        return module.Target(report, settings, configuration), report

    def test_reset_uses_the_configured_command_and_invalidates(self):
        target, report = self.target(command="monitor reset halt")
        result = target.reset()
        self.assertEqual(result["outcome"], "halted")
        self.assertEqual(result["command"], "monitor reset halt")
        self.assertEqual(self.commands, ["monitor reset halt",
                                         "maintenance flush register-cache"])
        self.assertEqual([step["step"] for step in result["invalidation"]],
                         ["flush_register_cache", "invalidate_cached_frames"])
        self.assertTrue(all(step["status"] == "done" for step in result["invalidation"]))
        self.assertEqual(self.invalidate_calls, 1)
        self.assertEqual(result["registers"]["pc"], 0x8000100)
        self.assertEqual(report["resets"][-1]["command"], "monitor reset halt")

    def test_reset_prefers_a_session_override(self):
        target, _report = self.target(command="monitor reset halt")
        with patch.dict(os.environ, {"STM32_GDBTEST_RESET_COMMAND": "monitor reset"}):
            result = target.reset()
        self.assertEqual(result["command"], "monitor reset")

    def test_reset_falls_back_to_the_backend_default(self):
        target, _report = self.target(profile={"reset_halt": "monitor reset halt"})
        result = target.reset()
        self.assertEqual(result["command"], "monitor reset halt")

    def test_reset_uses_the_generic_default_without_a_backend_value(self):
        target, _report = self.target()
        result = target.reset()
        self.assertEqual(result["command"], RESET_COMMAND)

    def test_reset_rejects_a_blank_configured_command(self):
        target, _report = self.target(command="   ")
        with self.assertRaises(ApiError) as caught:
            target.reset()
        self.assertEqual(caught.exception.code, "invalid_command")

    def test_reset_refuses_active_points(self):
        target, _report = self.target()
        target.breakpoint("app_loop")
        with self.assertRaises(ApiError) as caught:
            target.reset()
        self.assertEqual(caught.exception.code, "active_points")
        self.assertEqual(caught.exception.details["effect"], "none")
        self.assertEqual(self.commands, [])

    def test_reset_proceeds_after_points_are_removed(self):
        target, _report = self.target()
        point = target.breakpoint("app_loop")
        point.remove()
        result = target.reset()
        self.assertEqual(result["outcome"], "halted")

    def test_reset_reports_a_failed_command_and_still_invalidates(self):
        target, _report = self.target(command="monitor reset halt")
        self.reset_failure = "monitor reset halt"
        with self.assertRaises(ApiError) as caught:
            target.reset()
        details = caught.exception.details
        self.assertEqual(details["code"], "command_failed")
        self.assertEqual(details["stage"], "command")
        self.assertEqual(details["effect"], "unknown")
        self.assertIsInstance(caught.exception.__cause__, FakeError)
        self.assertEqual([step["status"] for step in details["invalidation"]], ["done", "done"])
        self.assertIn("monitor reset halt", self.commands)

    def test_reset_records_failed_invalidation_steps(self):
        target, _report = self.target(command="monitor reset halt")

        def failing_execute(command, **options):
            self.commands.append(command)
            if command.startswith("monitor"):
                return ""
            raise FakeError("maintenance unavailable")

        self.gdb.execute = failing_execute
        result = target.reset()
        self.assertEqual([step["status"] for step in result["invalidation"]],
                         ["failed", "done"])
        self.assertIn("maintenance", result["invalidation"][0]["detail"])


if __name__ == "__main__":
    unittest.main()
