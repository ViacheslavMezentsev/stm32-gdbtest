"""ТЗ API 6.10: interactive run for a scenario author; synthetic stand, no debug server or GDB."""
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import uuid
from unittest.mock import patch

from stm32_gdbtest import interactive
from stm32_gdbtest.runner import ROOT, run, wait_interactive

SNAPSHOT = type("Snapshot", (), {"config": {"target": {}, "api": {"schema": 1}}, "capture_results": False})()


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class InteractiveRunTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "build/host-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.debugpy = self.root / "libs"
        (self.debugpy / "debugpy").mkdir(parents=True)
        (self.debugpy / "debugpy" / "__init__.py").write_text("")
        self.session = dict(root=str(self.root), out=str(self.root / "hwtest/runs"), stand="mock.toml")
        self.test = dict(id="HW_STEP", timeout_s=10)

    def run_mocked(self, **options):
        stand = dict(backend="stlink", serial="TEST" + uuid.uuid4().hex)
        with patch.dict(os.environ, {}, clear=False), \
                patch("stm32_gdbtest.runner.load_stand", return_value=stand), \
                patch("stm32_gdbtest.runner.capture", return_value=SNAPSHOT), \
                patch("stm32_gdbtest.runner.probe_lock", return_value=contextlib.nullcontext()), \
                patch("stm32_gdbtest.runner.execute") as execute, \
                contextlib.redirect_stdout(io.StringIO()) as output:
            code = run(self.session, self.test, **options)
        return code, execute, output.getvalue()

    def results(self, name):
        return [json.loads(path.read_text()) for path in (self.root / "hwtest" / name).glob("*/result.json")]

    def test_interactive_run_is_isolated_and_has_no_time_limit(self):
        port = free_port()
        code, execute, output = self.run_mocked(interactive=True, debug_port=port, debugpy=self.debugpy)
        execute.assert_called_once()
        session, test, stand, out, report, timeout, profile = execute.call_args.args
        self.assertIsNone(timeout)
        self.assertEqual(session["_interactive"], {"port": port, "debugpy": str(self.debugpy.resolve())})
        self.assertEqual(out.parent.name, "interactive-runs")
        self.assertEqual(self.results("runs"), [])
        [result] = self.results("interactive-runs")
        self.assertEqual(result["execution_kind"], "interactive")
        self.assertIn("excluded from automated runs", output)
        self.assertNotEqual(code, 0)  # the mocked execute leaves the default ERROR: no silent PASS

    def test_automated_run_is_unchanged(self):
        code, execute, output = self.run_mocked()
        session, test, stand, out, report, timeout, profile = execute.call_args.args
        self.assertEqual(timeout, 10)
        self.assertNotIn("_interactive", session)
        self.assertEqual(out.parent.name, "runs")
        [result] = self.results("runs")
        self.assertNotIn("execution_kind", result)
        self.assertFalse((self.root / "hwtest/interactive-runs").exists())
        self.assertNotIn("Interactive", output)

    def test_interactive_rejects_timeout_prepare_busy_port_and_missing_debugpy(self):
        busy = socket.socket()
        busy.bind(("127.0.0.1", 0))
        self.addCleanup(busy.close)
        cases = [(dict(timeout=5), "no time limit"), (dict(prepare_only=True), "needs a stand"),
                 (dict(debug_port=busy.getsockname()[1]), "is busy"),
                 (dict(debugpy=self.root / "empty"), "debugpy not found")]
        for number, (extra, message) in enumerate(cases):
            with self.subTest(message=message):
                # A separate output root per case: run directories are named by time and PID,
                # and the Windows clock may give two quick in-process runs the same stamp.
                self.session = dict(self.session, out=str(self.root / f"case{number}/runs"))
                options = dict(interactive=True, debug_port=free_port(), debugpy=self.debugpy)
                options.update(extra)
                code, execute, _ = self.run_mocked(**options)
                self.assertEqual(code, 2)
                execute.assert_not_called()
                [result] = [json.loads(path.read_text())
                            for path in (self.root / f"case{number}/interactive-runs").glob("*/result.json")]
                self.assertIn(message, result["error"])
                self.assertEqual(list((self.root / f"case{number}/runs").glob("*/result.json")), [])

    def test_wait_has_no_limit_and_announces_once(self):
        ready = self.root / "ready.json"
        script = ("import time, pathlib, sys; time.sleep(0.3); pathlib.Path(sys.argv[1]).write_text('{}'); "
                  "time.sleep(1.2); sys.exit(77)")
        client = subprocess.Popen([sys.executable, "-c", script, str(ready)])
        started = time.monotonic()
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = wait_interactive(client, ready, 5678)
        self.assertEqual(code, 77)
        self.assertGreaterEqual(time.monotonic() - started, 1.4)
        self.assertEqual(output.getvalue().count("attach the debugger to 127.0.0.1:5678"), 1)
        # The automated path keeps its limit: the same process would be stopped by client.wait(timeout).
        client = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(5)"])
        self.addCleanup(lambda: (client.kill(), client.wait()))
        with self.assertRaises(subprocess.TimeoutExpired):
            client.wait(timeout=0.5)

    def test_debugpy_discovery(self):
        home = self.root / "home"
        for version in ("2026.6.0", "2026.10.0"):
            package = home / ".vscode/extensions" / f"ms-python.debugpy-{version}-win32-x64" / "bundled/libs/debugpy"
            package.mkdir(parents=True)
            (package / "__init__.py").write_text("")
        with patch.dict(os.environ, {"STM32_GDBTEST_DEBUGPY": ""}):
            self.assertIn("2026.10.0", str(interactive.debugpy_directory(home=home)))
        with patch.dict(os.environ, {"STM32_GDBTEST_DEBUGPY": str(self.debugpy)}):
            self.assertEqual(interactive.debugpy_directory(home=home), self.debugpy.resolve())
        with patch.dict(os.environ, {"STM32_GDBTEST_DEBUGPY": ""}), self.assertRaises(RuntimeError):
            interactive.debugpy_directory(home=self.root / "nobody")
        for port in (0, 70000, "5678"):
            with self.assertRaises(ValueError):
                interactive.check_port(port)

    def test_cli_rejects_mixed_options_before_reading_the_session(self):
        cli = str(ROOT / "stm32_gdbtest/cli.py")
        missing = str(self.root / "missing.json")
        for extra, message in (([ "--debug-port", "5678"], "require --interactive"),
                               (["--interactive", "--timeout", "5"], "no time limit"),
                               (["--interactive", "--prepare-only"], "no time limit")):
            with self.subTest(extra=extra):
                proc = subprocess.run([sys.executable, "-B", cli, "run", "--session", missing, "--test", "X"] + extra,
                                      capture_output=True, text=True, timeout=60)
                self.assertEqual(proc.returncode, 2)
                self.assertIn(message, proc.stderr)


if __name__ == "__main__":
    unittest.main()
