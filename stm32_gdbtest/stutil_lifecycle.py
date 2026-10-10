"""Bounded st-util idle observation, shared with the standalone SSH helper (Python 3.8+)."""

import re
import time

IDLE_TIMEOUT_S = 5.0


class IdleLog:
    """Observe complete events from exactly one process generation and port."""

    def __init__(self, port, offset=0, control_markers=True):
        self.port = int(port)
        self.offset = offset
        self.previous = b""
        self.snapshot = b""
        self.idle = False
        self.connected = False
        self.error = None
        self.control_markers = control_markers

    def observe(self, data):
        if len(data) < self.offset or not data[self.offset:].startswith(self.snapshot):
            self.error = "server log was truncated or replaced"
        current = data[self.offset:]
        self.snapshot = current
        complete = current[:current.rfind(b"\n") + 1]
        for line in complete[len(self.previous):].decode("utf-8", "replace").splitlines():
            if self.control_markers and line.startswith("STM32_GDBTEST_REMOTE ") and any(
                    token in line for token in ("error=", "exit=", "server-result=")):
                self.error = "remote server ended or refused the session"
            if line.endswith("GDB connected."):
                self.connected = True
                self.idle = False
            match = re.search(r"Listening at \*:(\d+)\s*$", line)
            if match:
                self.idle = int(match[1]) == self.port
        self.previous = complete


def wait_idle(state, read, alive, *, require_connection=True, limit=IDLE_TIMEOUT_S,
              clock=time.monotonic, sleep=time.sleep):
    """No TCP probe: the next GDB connection is attempted only after log evidence."""
    start = clock()
    while True:
        live = alive()
        state.observe(read())
        elapsed = clock() - start
        reason = ("process_exit" if not live else state.error or
                  ("deadline" if elapsed >= limit else
                   "ready" if state.idle and (state.connected or not require_connection) else None))
        if reason is not None:
            # A simultaneous exit takes priority over an earlier ready event.
            if reason == "ready" and not alive():
                reason = "process_exit"
            if reason == "ready" and clock() - start >= limit:
                reason = "deadline"
            return dict(ready=reason == "ready", reason=reason, elapsed_s=round(clock() - start, 6), limit_s=limit)
        sleep(min(0.05, limit - elapsed))
