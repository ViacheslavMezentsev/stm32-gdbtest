"""Remote side of a GDB server started over SSH (ТЗ 5.18); runs on the stand host.

The runner sends this file's source over SSH, so the stand host needs no checkout of
the module and only Python >= 3.8 (the Ubuntu 20.04 system python3). It must stay
self-contained: standard library only, no f-string features newer than 3.8.

Protocol on stdout (the SSH channel), one marker per line:
  STM32_GDBTEST_REMOTE ready-to-start port=<n> dir=<path>   before the server starts
  STM32_GDBTEST_REMOTE error=<code> <text>                  refusal, exit code 3
  STM32_GDBTEST_REMOTE log=<name>                           followed by a log file
  STM32_GDBTEST_REMOTE server-result=<json>                 actual child exit after cleanup
  STM32_GDBTEST_REMOTE exit=<code>                          final line
The server is stopped when stdin reaches EOF (the runner closed or lost the session) or,
with "heartbeat_s" in the config, when stdin brings no data for that long (the link died
without closing the connection); then the logs are not sent, as the channel may be stalled.
"""

import base64
import errno
import fcntl
import json
import os
import select
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time

from stutil_lifecycle import IdleLog, wait_idle

MARK = "STM32_GDBTEST_REMOTE"
OUTPUT = None


def say(text):
    if OUTPUT is not None:
        OUTPUT.write((MARK + " " + text + "\n").encode("utf-8"))
        return
    sys.stdout.write(MARK + " " + text + "\n")
    sys.stdout.flush()


class OutputRelay:
    """A stalled SSH reader must not prevent local cleanup of the USB process."""

    def __init__(self):
        self.pending = b""
        self.failed = False
        os.set_blocking(sys.stdout.fileno(), False)

    def write(self, data):
        if len(self.pending) + len(data) > 1024 * 1024:
            self.failed = True
            self.pending = b""
        if not self.failed:
            self.pending += data
            self.flush()

    def flush(self):
        if self.pending:
            try:
                sent = os.write(sys.stdout.fileno(), self.pending)
                self.pending = self.pending[sent:]
            except BlockingIOError:
                pass
            except OSError:
                self.failed = True
                self.pending = b""

    def finish(self):
        deadline = time.monotonic() + 1
        while self.pending and time.monotonic() < deadline:
            self.flush()
            time.sleep(0.01)


class ServerLog:
    """Keep child output off the SSH pipe; inspect it locally even when that pipe is lost."""

    def __init__(self, directory):
        self.path = os.path.join(directory, "server-output.log")
        self.writer = open(self.path, "wb")
        self.reader = open(self.path, "rb")
        self.data = b""
        self.forwarded = 0

    def read(self):
        self.data += self.reader.read()
        end = self.data.rfind(b"\n") + 1
        lines = self.data[self.forwarded:end].splitlines(keepends=True)
        # Child text must not impersonate helper control records.
        for line in lines:
            if line.startswith(MARK.encode("ascii") + b" "):
                line = b"SERVER: " + line
            OUTPUT.write(line)
        self.forwarded = end
        OUTPUT.flush()
        return self.data

    def close(self):
        self.writer.close()
        self.reader.close()


def lock_path(identity):
    base = os.environ.get("STM32_GDBTEST_LOCK_DIR") or tempfile.gettempdir()
    return os.path.join(base, "stm32-gdbtest-locks", "probe.v1." + identity + ".lock")


def acquire(identity):
    """Same file, flock and owner record as the Linux runner (ТЗ 5.4.8, 5.4.9)."""
    path = lock_path(identity)
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    if os.stat(directory).st_uid == os.getuid():
        os.chmod(directory, 0o1777)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        os.close(descriptor)
        if exc.errno in (errno.EWOULDBLOCK, errno.EACCES):
            raise LookupError("busy Debugger already owned by another runner on the stand host")
        raise
    previous = os.pread(descriptor, 256, 0).decode("ascii", "replace").strip()
    if previous:
        os.ftruncate(descriptor, 0)
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
        raise LookupError("abandoned Abandoned debugger ownership on the stand host: check orphan "
                          "GDB/server processes before retry (" + previous + ")")
    os.pwrite(descriptor, ("pid=%d remote\n" % os.getpid()).encode("ascii"), 0)
    return descriptor


def release(descriptor):
    os.ftruncate(descriptor, 0)
    fcntl.flock(descriptor, fcntl.LOCK_UN)
    os.close(descriptor)


def port_free(port):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def stop_group(process):
    signals = []
    for sig, grace in ((signal.SIGTERM, 3.0), (signal.SIGKILL, 5.0)):
        try:
            os.killpg(process.pid, sig)
            signals.append(int(sig))
        except (ProcessLookupError, PermissionError):
            break
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            process.poll()
            try:
                os.killpg(process.pid, 0)
            except (ProcessLookupError, PermissionError):
                return signals
            time.sleep(0.05)
    if process.poll() is None:
        process.kill()
        signals.append(int(signal.SIGKILL))
    process.wait(timeout=5)
    return signals


def serve(config):
    global OUTPUT
    port = config["port"]
    if not port_free(port):
        say("error=port Remote port %d is busy" % port)
        return 3
    descriptor = acquire(config["identity"])
    directory = tempfile.mkdtemp(prefix="stm32-gdbtest-")
    process = None
    lost = False
    reason = "process_exit"
    signals = []
    child_log = None
    idle = None
    try:
        command = [item.replace("{port}", str(port)).replace("{dir}", directory) for item in config["command"]]
        executable = shutil.which(command[0])
        if not executable:
            say("error=executable GDB server not found on the stand host: " + command[0])
            return 3
        command[0] = executable
        if config.get("backend") == "st-util":
            OUTPUT = OutputRelay()
            child_log = ServerLog(directory)
        say("ready-to-start port=%d dir=%s" % (port, directory))
        process = subprocess.Popen(command, cwd=directory, stdin=subprocess.DEVNULL,
                                   stdout=child_log.writer if child_log else sys.stdout,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        heartbeat = config.get("heartbeat_s")
        last = time.monotonic()
        while process.poll() is None:
            if child_log:
                child_log.read()
            readable, _, _ = select.select([sys.stdin], [], [], 0.05 if child_log else 0.5)
            if readable:
                if not os.read(sys.stdin.fileno(), 4096):
                    reason = "stdin_eof"
                    break
                last = time.monotonic()
            elif heartbeat and time.monotonic() - last > heartbeat:
                lost = True
                reason = "heartbeat_timeout"
                break
    finally:
        try:
            if process is not None:
                try:
                    if child_log:
                        idle = wait_idle(IdleLog(port, control_markers=False), child_log.read,
                                         lambda: process.poll() is None, require_connection=False)
                except Exception as error:
                    idle = dict(ready=False, reason="idle observation failed: " + str(error),
                                elapsed_s=0, limit_s=5)
                finally:
                    # Even failure of the observer must not leave the USB server running.
                    signals = stop_group(process)
                if child_log:
                    child_log.read()
            try:
                for name in [] if lost else config.get("logs", []):
                    path = os.path.join(directory, name)
                    if os.path.isfile(path):
                        say("log=" + name)
                        with open(path, "rb") as stream:
                            sys.stdout.write(stream.read().decode("utf-8", "replace") + "\n")
                sys.stdout.flush()
            except OSError:
                pass  # the session is gone (runner closed or lost); logs stay unsent
            if child_log:
                child_log.close()
            shutil.rmtree(directory, ignore_errors=True)
        finally:
            release(descriptor)
    # ТЗ 5.18.9: evaluate the actual child result only after cleanup and reap.
    code = process.wait(timeout=5)
    result = dict(returncode=code, reason=reason, signals=signals)
    if idle is not None:
        result["idle"] = idle
    say("server-result=" + json.dumps(result))
    return code


def check(config):
    """doctor: Python, server executable and ST-Link/J-Link USB access on the stand host."""
    found = []
    root = "/sys/bus/usb/devices"
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        def attribute(key):
            try:
                with open(os.path.join(root, name, key)) as stream:
                    return stream.read().strip()
            except OSError:
                return ""
        vendor = attribute("idVendor")
        if vendor not in ("0483", "1366") or attribute("bDeviceClass") == "09":
            continue
        if vendor == "0483" and attribute("idProduct").lower() not in config["stlink_products"]:
            continue
        node = None
        if attribute("busnum") and attribute("devnum"):
            node = "/dev/bus/usb/%03d/%03d" % (int(attribute("busnum")), int(attribute("devnum")))
        found.append(dict(kind="J-Link" if vendor == "1366" else "ST-Link", product_id=attribute("idProduct"),
                          serial=attribute("serial"), node=node,
                          access=bool(node and os.access(node, os.R_OK | os.W_OK))))
    lock_dir = os.path.dirname(lock_path(config["identity"]))
    print(MARK + " check=" + json.dumps(dict(
        python=sys.version.split()[0], machine=os.uname().machine,
        executable=shutil.which(config["executable"]), usb=found,
        lock_dir=lock_dir, lock_writable=os.access(lock_dir if os.path.isdir(lock_dir)
                                                   else os.path.dirname(lock_dir), os.W_OK))))
    return 0


def main():
    config = json.loads(base64.b64decode(sys.argv[-1]).decode("utf-8"))
    for sig in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, lambda number, frame: sys.exit(128 + number))
    code = 3
    try:
        code = check(config) if config["mode"] == "check" else serve(config)
    except LookupError as exc:
        kind, _, text = str(exc.args[0]).partition(" ")
        say("error=%s %s" % (kind, text))
        code = 3
    finally:
        try:
            say("exit=%d" % code)
        except OSError:
            pass
        if OUTPUT is not None:
            OUTPUT.finish()
    return code


if __name__ == "__main__":
    sys.exit(main())
