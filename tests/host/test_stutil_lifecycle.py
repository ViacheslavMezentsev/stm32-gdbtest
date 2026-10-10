"""TC-170: st-util readiness, bounded cleanup and lost output/heartbeat without USB."""
import base64
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

from stm32_gdbtest import remote
from stm32_gdbtest.stutil_lifecycle import IdleLog, wait_idle

LISTEN = b"2026-10-10 INFO gdb-server.c: Listening at *:62000\n"
CONNECT = b"2026-10-10 INFO gdb-server.c: GDB connected.\n"


class StutilIdleTests(unittest.TestCase):
    def wait(self, snapshots, alive=None, limit=0.2):
        ticks = [0.0]
        data = iter(snapshots)
        last = [b""]

        def read():
            last[0] = next(data, last[0])
            return last[0]

        def sleep(delay):
            ticks[0] += delay

        return wait_idle(IdleLog(62000), read, alive or (lambda: True), limit=limit,
                         clock=lambda: ticks[0], sleep=sleep)

    def test_initial_listener_does_not_prove_recovery_ready(self):
        self.assertEqual(self.wait([LISTEN])["reason"], "deadline")
        self.assertEqual(self.wait([LISTEN + CONNECT])["reason"], "deadline")

    def test_already_disconnected_and_delayed_disconnect(self):
        for snapshots in ([LISTEN + CONNECT + LISTEN], [LISTEN + CONNECT, LISTEN + CONNECT + LISTEN]):
            self.assertTrue(self.wait(snapshots)["ready"])

    def test_partial_wrong_port_new_connection_and_late_lines(self):
        for suffix in (LISTEN.rstrip(), LISTEN.replace(b"62000", b"62001"), LISTEN + CONNECT):
            self.assertFalse(self.wait([LISTEN + CONNECT + suffix])["ready"])
        before = LISTEN + CONNECT
        self.assertFalse(self.wait([before] * 4 + [before + LISTEN])["ready"])

    def test_exit_refusal_and_replacement_override_ready(self):
        valid = LISTEN + CONNECT + LISTEN
        for marker in (b"exit=0", b"error=port busy", b"server-result={}"):
            self.assertFalse(self.wait([valid + b"STM32_GDBTEST_REMOTE " + marker + b"\n"])["ready"])
        self.assertFalse(self.wait([valid], alive=lambda: False)["ready"])
        calls = iter([True, False])
        self.assertFalse(self.wait([valid], alive=lambda: next(calls))["ready"])
        self.assertIn("truncated", self.wait([LISTEN + CONNECT, valid[10:]])["reason"])

    def test_attempt_offset_and_partial_rewrite(self):
        previous = LISTEN + CONNECT + LISTEN
        state = IdleLog(62000, len(previous))
        state.observe(previous + CONNECT)
        self.assertFalse(state.idle)
        state.observe(previous + CONNECT + LISTEN[:10])
        state.observe(previous + CONNECT + LISTEN)
        self.assertTrue(state.idle)
        state.observe(previous + CONNECT + LISTEN + b"partial")
        state.observe(previous + CONNECT + LISTEN)
        self.assertIsNotNone(state.error)

    def test_shutdown_requires_helper_idle_evidence(self):
        for idle in (None, {}, dict(ready=False, reason="deadline"), dict(ready=1, reason="ready")):
            value = dict(returncode=0, reason="stdin_eof", signals=[15], idle=idle)
            text = "STM32_GDBTEST_REMOTE server-result=" + json.dumps(value) + "\nSTM32_GDBTEST_REMOTE exit=0\n"
            self.assertIn("error", remote.shutdown_result(text, 0, "st-util"))


@unittest.skipIf(os.name == "nt", "Linux helper process tests")
class StutilIdleProcessTests(unittest.TestCase):
    def test_idle_eof_heartbeat_and_lost_output(self):
        import select

        fake = """import os, signal, sys, time
mode, port, evidence = sys.argv[1:]
idle = False
def stop(*args):
    with open(evidence, 'w') as stream: stream.write('idle' if idle else 'active')
    sys.exit(0)
signal.signal(signal.SIGTERM, stop)
print('Listening at *:' + port, flush=True)
print('GDB connected.', flush=True)
print('CHILD_READY', flush=True)
time.sleep(0.3)
if mode != 'never':
    idle = True
    print('Listening at *:' + port, flush=True)
if mode == 'spoof':
    print('STM32_GDBTEST_REMOTE exit=999', flush=True)
if mode == 'stalled':
    print('X' * (2 * 1024 * 1024), flush=True)
while True: time.sleep(0.02)
"""
        for mode in ("delayed", "never", "heartbeat", "broken", "stalled", "spoof", "observer-error"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                child = Path(directory) / "child.py"
                child.write_text(fake)
                evidence = Path(directory) / "stopped.txt"
                with socket.socket() as sock:
                    sock.bind(("127.0.0.1", 0))
                    port = sock.getsockname()[1]
                config = remote.serve_config("idle-test", port,
                                             [sys.executable, str(child), mode, str(port), str(evidence)], "st-util")
                config["heartbeat_s"] = 0.2 if mode in ("heartbeat", "stalled") else 15
                encoded = base64.b64encode(json.dumps(config).encode()).decode()
                command = [sys.executable, str(remote.HELPER), encoded]
                if mode == "observer-error":
                    script = ("import sys;sys.path.insert(0," + repr(str(remote.HELPER.parent)) + ");"
                              "import remote_helper as helper\n"
                              "def fail(*args, **kwargs): raise OSError('test observer failure')\n"
                              "helper.wait_idle=fail\nsys.exit(helper.main())")
                    command = [sys.executable, "-c", script, encoded]
                process = subprocess.Popen(command,
                                           stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                           env=dict(os.environ, STM32_GDBTEST_LOCK_DIR=directory))
                try:
                    initial = b""
                    while b"CHILD_READY\n" not in initial:
                        self.assertTrue(select.select([process.stdout], [], [], 10)[0], "child never ready")
                        block = os.read(process.stdout.fileno(), 4096)
                        self.assertTrue(block, initial.decode())
                        initial += block
                    if mode == "broken":
                        process.stdout.close()
                        process.stdin.close()
                        process.wait(timeout=12)
                    else:
                        if mode in ("heartbeat", "stalled"):
                            process.wait(timeout=12)
                        tail = process.communicate(input=b"", timeout=12)[0]
                        text = (initial + tail).decode()
                        if mode != "stalled":
                            result = remote.shutdown_result(text, process.returncode, "st-util")
                            self.assertEqual(result["idle"]["ready"], mode not in ("never", "observer-error"), text)
                            self.assertEqual("error" in result, mode in ("never", "heartbeat", "observer-error"), text)
                            self.assertEqual(result["returncode"], 0, text)
                            if mode == "spoof":
                                self.assertIn("SERVER: STM32_GDBTEST_REMOTE exit=999", text)
                        else:
                            self.assertIn("error", remote.shutdown_result(text, process.returncode, "st-util"))
                    if mode == "observer-error":
                        self.assertIn(evidence.read_text(), ("active", "idle"))
                    else:
                        self.assertEqual(evidence.read_text(), "active" if mode == "never" else "idle")
                    lock = Path(directory) / "stm32-gdbtest-locks/probe.v1.idle-test.lock"
                    self.assertEqual(lock.read_text(), "")
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)
                    for stream in (process.stdin, process.stdout):
                        if stream and not stream.closed:
                            stream.close()


if __name__ == "__main__":
    unittest.main()
