"""TC-169: actual remote child exit and preservation of the original run outcome."""
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from stm32_gdbtest import remote


def completion(code, reason="stdin_eof", signals=None):
    value = dict(returncode=code, reason=reason, signals=[15] if signals is None else signals)
    value["idle"] = dict(ready=True, reason="ready", elapsed_s=0, limit_s=5)
    return "STM32_GDBTEST_REMOTE server-result=" + json.dumps(value) + f"\nSTM32_GDBTEST_REMOTE exit={code}\n"


class RemoteShutdownTests(unittest.TestCase):
    def _runner_report(self, teardown="reset_run", idle=True):
        from stm32_gdbtest import runner
        from stm32_gdbtest.profile import load_profile
        from test_prepare import PROFILE, SECTIONS

        parent = runner.ROOT / "build/host-tests"
        parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as directory:
            root = Path(directory)
            elf = root / "input.elf"
            elf.write_bytes(b"mock ELF")
            out = root / "output"
            out.mkdir()
            report = dict(status="ERROR")
            session = dict(root=str(root), elf=str(elf), gdb="arm-none-eabi-gdb", profile=str(PROFILE))
            stand = dict(backend="st-util", serial="0" * 24, flash="verify-only", remote={"host": "fake"})
            server, client = MagicMock(), MagicMock()
            server.poll.return_value = None
            server.returncode = None
            recoveries = []

            def finish_server():
                with (out / "server.log").open("a") as stream:
                    stream.write(completion(-6))
                server.returncode = 250
                server.poll.return_value = 250

            server.stdin.close.side_effect = finish_server

            def spawn(command, **kwargs):
                if command[0] == "ssh":
                    kwargs["stdout"].write(b"Listening at *:62000\n")
                    kwargs["stdout"].flush()
                    kwargs["stderr"].write(b"Local forwarding listening on\n")
                    kwargs["stderr"].flush()
                    return server
                with (out / "server.log").open("ab") as stream:
                    stream.write(b"GDB connected.\n" + (b"Listening at *:62000\n" if idle else b""))
                result = dict(id="TEST", status="PASS", elf_sha256=report["elf_sha256"],
                              bin_sha256=report["bin_sha256"], teardown=teardown, checks=[{"passed": True}])
                (out / "agent-result.json").write_text(json.dumps(result))
                client.wait.return_value = 0
                return client

            def tools(command, **kwargs):
                if "--gap-fill=0xFF" in command:
                    Path(command[-1]).write_bytes(bytes(range(32)))
                if any("target extended-remote" in arg for arg in command):
                    self.assertTrue(report["recovery_wait"]["ready"])
                    recoveries.append(command)

            original_wait = runner.wait_idle

            def short_wait(*args, **kwargs):
                return original_wait(*args, **kwargs, limit=0.02)

            with patch.object(runner.subprocess, "check_output", return_value=SECTIONS.encode()), \
                    patch.object(runner.subprocess, "run", side_effect=tools), \
                    patch.object(runner.subprocess, "Popen", side_effect=spawn), \
                    patch.object(runner, "stop_tree"), \
                    patch.object(runner, "server_spec", return_value=dict(command=["fake"], ready="READY",
                                                                         reset_halt="reset", finish=["finish"])), \
                    patch.object(remote, "ssh_command", return_value=["ssh"]), \
                    patch.object(remote, "remote_script", return_value="fake-script"), \
                    patch.object(runner, "wait_idle", side_effect=short_wait), \
                    patch.object(remote, "Heartbeat"):
                with patch.object(runner, "remote_port", return_value=62000):
                    runner.execute(session, dict(id="TEST", contracts=[]), stand, out, report, 10, load_profile(PROFILE))
            return report, recoveries

    def test_runner_checks_shutdown_after_the_agent_report(self):
        report, recoveries = self._runner_report()
        self.assertEqual(report["status_before_cleanup"], "PASS", report)
        self.assertEqual(report["status"], "ERROR")
        self.assertEqual(report["remote_server"]["returncode"], -6)
        self.assertEqual(report["checks"], [{"passed": True}])
        self.assertEqual(recoveries, [])

    def test_runner_waits_before_single_recovery_attempt(self):
        report, recoveries = self._runner_report(teardown=None)
        self.assertEqual(len(recoveries), 1)
        self.assertEqual(report["teardown"], "reset_run (host recovery)")
        self.assertTrue(report["shutdown_wait"]["ready"])

    def test_runner_does_not_reconnect_when_idle_is_unknown(self):
        report, recoveries = self._runner_report(teardown=None, idle=False)
        self.assertEqual(recoveries, [])
        self.assertEqual(report["recovery_wait"]["reason"], "deadline")
        self.assertFalse(report["shutdown_wait"]["ready"])
        self.assertIn("teardown_error", report)
        self.assertEqual(report["remote_server"]["returncode"], -6)

    def test_cleanup_failure_preserves_all_original_outcomes(self):
        for status in ("PASS", "FAIL", "SKIP", "ERROR"):
            with self.subTest(status=status):
                report = dict(status=status, status_before_cleanup=status, checks=[{"passed": False}],
                              error="original cause", skip_reason="original skip")
                remote.record_shutdown(report, completion(-6), 250, "st-util")
                self.assertEqual(report["status"], "ERROR")
                self.assertEqual(report["status_before_cleanup"], status)
                self.assertEqual(report["error"], "original cause")
                self.assertEqual(report["skip_reason"], "original skip")
                self.assertEqual(report["checks"], [{"passed": False}])
                self.assertEqual(report["remote_server"]["returncode"], -6)

    def test_normal_exit_and_backend_specific_sigterm(self):
        self.assertNotIn("error", remote.shutdown_result(completion(0), 0, "st-util"))
        for backend in ("openocd", "jlink", "stlink"):
            self.assertNotIn("error", remote.shutdown_result(completion(-15), 241, backend))
        self.assertIn("error", remote.shutdown_result(completion(-15), 241, "st-util"))
        self.assertIn("error", remote.shutdown_result(completion(-15, signals=[]), 241, "openocd"))

    def test_crash_kill_heartbeat_and_premature_exit_are_errors(self):
        for code, reason, signals in [(7, "stdin_eof", [15]), (-6, "stdin_eof", [15]),
                                      (-9, "stdin_eof", [15, 9]), (0, "stdin_eof", [15, 9]),
                                      (0, "heartbeat_timeout", [15]), (0, "process_exit", [])]:
            with self.subTest(code=code, reason=reason):
                result = remote.shutdown_result(completion(code, reason, signals), code & 255, "st-util")
                self.assertIn("error", result)
                self.assertEqual(result["returncode"], code)

    def test_missing_corrupt_duplicate_partial_and_ssh_conflicts(self):
        for text, code in [("", 0), (completion(0) * 2, 0), (completion(0).rstrip(), 0),
                           (completion(0), 255), (completion(-6), 0),
                           (completion(0).replace('"returncode": 0', '"returncode": true'), 0),
                           (completion(0).replace('"reason": "stdin_eof"', '"reason": []'), 0),
                           (completion(0).replace('{"returncode"', '{broken'), 0)]:
            with self.subTest(text=text):
                self.assertIn("error", remote.shutdown_result(text, code, "st-util"))


@unittest.skipIf(os.name == "nt", "Linux helper process tests")
class RemoteShutdownProcessTests(unittest.TestCase):
    def test_real_child_results_after_cleanup(self):
        import select

        fake = """import os, resource, signal, sys, time
resource.setrlimit(resource.RLIMIT_CORE, (0,0))
mode=sys.argv[1]
if mode=='clean': signal.signal(signal.SIGTERM, lambda *args: sys.exit(0))
if mode=='error': signal.signal(signal.SIGTERM, lambda *args: sys.exit(7))
if mode=='abort': signal.signal(signal.SIGTERM, lambda *args: os.abort())
if mode=='ignore': signal.signal(signal.SIGTERM, signal.SIG_IGN)
print('CHILD_READY', flush=True)
if mode=='natural': sys.exit(7)
if mode=='natural-zero': sys.exit(0)
while True: time.sleep(0.02)
"""
        for mode, expected in [("clean", 0), ("error", 7), ("abort", -6), ("ignore", -9), ("default", -15),
                               ("natural", 7), ("natural-zero", 0), ("heartbeat", -15)]:
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                child = Path(directory) / "child.py"
                child.write_text(fake)
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                config = dict(mode="serve", identity="shutdown-test", port=port, logs=[],
                              command=[sys.executable, str(child), mode])
                if mode == "heartbeat":
                    config["heartbeat_s"] = 0.2
                encoded = base64.b64encode(json.dumps(config).encode()).decode()
                process = subprocess.Popen([sys.executable, str(remote.HELPER), encoded],
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           env=dict(os.environ, STM32_GDBTEST_LOCK_DIR=directory))
                try:
                    initial = b""
                    while b"CHILD_READY\n" not in initial:
                        self.assertTrue(select.select([process.stdout], [], [], 10)[0], "child never ready")
                        block = os.read(process.stdout.fileno(), 4096)
                        self.assertTrue(block, initial.decode())
                        initial += block
                    if mode in ("natural", "natural-zero", "heartbeat"):
                        process.wait(timeout=15)
                    tail = process.communicate(input=b"", timeout=15)[0]
                    text = (initial + tail).decode()
                    value = json.loads(remote.parse_marker(text, "server-result"))
                    self.assertEqual(value["returncode"], expected, text)
                    self.assertEqual(process.returncode, expected & 255, text)
                    expected_reason = ("process_exit" if mode.startswith("natural") else
                                       "heartbeat_timeout" if mode == "heartbeat" else "stdin_eof")
                    self.assertEqual(value["reason"], expected_reason)
                    self.assertEqual(9 in value["signals"], mode == "ignore")
                    lock = Path(directory) / "stm32-gdbtest-locks/probe.v1.shutdown-test.lock"
                    self.assertEqual(lock.read_text(), "")
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.communicate(timeout=15)


if __name__ == "__main__":
    unittest.main()
