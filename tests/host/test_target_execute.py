"""Debugger commands through `execute`: output, journal, truncation and errors."""
import importlib
import hashlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import ApiError
from stm32_gdbtest.configuration import DEFAULTS, EXECUTE_OUTPUT_LIMIT, Configuration, freeze

TYPE_CODE_INT = 8


class FakeError(Exception):
    pass


def make_config(limit=None):
    api = dict(schema=1, records=dict(DEFAULTS))
    if limit is not None:
        api["execute"] = dict(output_limit_chars=limit)
    return Configuration(freeze(dict(target={}, image=None, api=api)),
                         freeze(dict(target=None, api=None, image=None)), None, {})


class ExecuteTests(unittest.TestCase):
    def setUp(self):
        self.commands = []
        self.output = "pc 0x8000100\n"
        self.failure = None

        def execute(command, **options):
            self.commands.append(command)
            if self.failure is not None:
                raise FakeError(self.failure)
            return self.output

        self.gdb = types.SimpleNamespace(
            error=FakeError,
            execute=execute,
            parse_and_eval=lambda expression: types.SimpleNamespace(
                is_optimized_out=False, fetch_lazy=lambda: None, __int__=lambda self: 0),
            newest_frame=lambda: types.SimpleNamespace(name=lambda: "main", pc=lambda: 0x8000100),
            events=types.SimpleNamespace(stop=Mock()),
        )

    def target(self, limit=None):
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
        report = {"checks": [], "executions": []}
        target = module.Target(report, {"breakpoint_limit": 4, "fault_handlers": []},
                               make_config(limit))
        return target, report

    def test_execute_returns_the_full_output_and_journals_it(self):
        target, report = self.target()
        self.assertEqual(target.execute("info registers pc"), self.output)
        entry = report["executions"][-1]
        self.assertEqual(entry["command"], "info registers pc")
        self.assertEqual(entry["stage"], "capture")
        self.assertEqual(entry["result"], "ok")
        self.assertEqual(entry["output_length"], len(self.output))
        self.assertFalse(entry["truncated"])
        self.assertNotIn("output_sha256", entry)
        self.assertEqual(entry["limit"], EXECUTE_OUTPUT_LIMIT)

    def test_execute_accepts_the_boundary_length(self):
        target, report = self.target(limit=16)
        self.output = "X" * 16
        self.assertEqual(target.execute("echo"), self.output)
        self.assertFalse(report["executions"][-1]["truncated"])
        self.output = "X" * 17
        self.assertEqual(target.execute("echo"), self.output)
        entry = report["executions"][-1]
        self.assertTrue(entry["truncated"])
        self.assertEqual(entry["output_length"], 17)
        self.assertEqual(entry["output_sha256"], hashlib.sha256(("X" * 17).encode()).hexdigest())

    def test_execute_uses_the_configured_limit(self):
        target, report = self.target(limit=8)
        self.output = "Y" * 9
        target.execute("echo")
        self.assertEqual(report["executions"][-1]["limit"], 8)

    def test_execute_rejects_an_invalid_limit(self):
        target, _report = self.target(limit=0)
        with self.assertRaises(ApiError) as caught:
            target.execute("echo")
        self.assertEqual(caught.exception.code, "invalid_limit")

    def test_execute_rejects_invalid_commands(self):
        target, report = self.target()
        for command in ("", "   ", 7, None, "info\nregisters", "info\rregisters"):
            with self.subTest(command=command):
                with self.assertRaises(ApiError) as caught:
                    target.execute(command)
                self.assertEqual(caught.exception.code, "invalid_command")
        self.assertEqual(report["executions"], [])

    def test_execute_reports_a_debugger_error_and_never_repeats(self):
        target, report = self.target()
        self.failure = "no such command"
        with self.assertRaises(ApiError) as caught:
            target.execute("nonsense")
        self.assertEqual(caught.exception.code, "command_failed")
        self.assertEqual(caught.exception.details["stage"], "command")
        self.assertIsInstance(caught.exception.__cause__, FakeError)
        self.assertEqual(self.commands, ["nonsense"])
        self.assertEqual(report["executions"][-1]["result"], "failed")

    def test_execute_rejects_a_non_string_result(self):
        target, _report = self.target()
        self.gdb.execute = lambda command, **options: 7
        with self.assertRaises(ApiError) as caught:
            target.execute("echo")
        self.assertEqual(caught.exception.code, "invalid_result")


if __name__ == "__main__":
    unittest.main()
