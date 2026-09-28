"""Remote side of a GDB server started over SSH (ТЗ 5.18); runs on the stand host.

The runner sends this file's source over SSH, so the stand host needs no checkout of
the module and only Python >= 3.8 (the Ubuntu 20.04 system python3). It must stay
self-contained: standard library only, no f-string features newer than 3.8.

Protocol on stdout (the SSH channel), one marker per line:
  STM32_GDBTEST_REMOTE ready-to-start port=<n> dir=<path>   before the server starts
  STM32_GDBTEST_REMOTE error=<code> <text>                  refusal, exit code 3
  STM32_GDBTEST_REMOTE log=<name>                           followed by a log file
  STM32_GDBTEST_REMOTE exit=<code>                          final line
The server is stopped when stdin reaches EOF (the runner closed or lost the session).
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

MARK = "STM32_GDBTEST_REMOTE"


def say(text):
    sys.stdout.write(MARK + " " + text + "\n")
    sys.stdout.flush()


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
    for sig, grace in ((signal.SIGTERM, 3.0), (signal.SIGKILL, 5.0)):
        try:
            os.killpg(process.pid, sig)
        except (ProcessLookupError, PermissionError):
            break
        deadline = time.monotonic() + grace
        while time.monotonic() < deadline:
            process.poll()
            try:
                os.killpg(process.pid, 0)
            except (ProcessLookupError, PermissionError):
                return
            time.sleep(0.05)
    if process.poll() is None:
        process.kill()
    process.wait(timeout=5)


def serve(config):
    port = config["port"]
    if not port_free(port):
        say("error=port Remote port %d is busy" % port)
        return 3
    descriptor = acquire(config["identity"])
    directory = tempfile.mkdtemp(prefix="stm32-gdbtest-")
    process = None
    try:
        command = [item.replace("{port}", str(port)).replace("{dir}", directory) for item in config["command"]]
        executable = shutil.which(command[0])
        if not executable:
            say("error=executable GDB server not found on the stand host: " + command[0])
            return 3
        command[0] = executable
        say("ready-to-start port=%d dir=%s" % (port, directory))
        process = subprocess.Popen(command, cwd=directory, stdin=subprocess.DEVNULL, stdout=sys.stdout,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        while process.poll() is None:
            readable, _, _ = select.select([sys.stdin], [], [], 0.5)
            if readable and not os.read(sys.stdin.fileno(), 4096):
                break
        return process.poll() or 0
    finally:
        try:
            if process is not None:
                stop_group(process)
            try:
                for name in config.get("logs", []):
                    path = os.path.join(directory, name)
                    if os.path.isfile(path):
                        say("log=" + name)
                        with open(path, "rb") as stream:
                            sys.stdout.write(stream.read().decode("utf-8", "replace") + "\n")
                sys.stdout.flush()
            except OSError:
                pass  # the session is gone (runner closed or lost); logs stay unsent
            shutil.rmtree(directory, ignore_errors=True)
        finally:
            release(descriptor)


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
    return code


if __name__ == "__main__":
    sys.exit(main())
