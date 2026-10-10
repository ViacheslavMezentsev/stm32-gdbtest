"""Bounded process lifetime and cross-project debugger ownership (Windows, Linux)."""

from contextlib import contextmanager
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time
import re


FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def spawn_options():
    """Popen options that let stop_tree reach every child of a server or GDB client."""
    if os.name == "nt":
        return {"creationflags": FLAGS}
    return {"start_new_session": True}  # ТЗ 6.10.2: own process group per child.


def stop_tree(process):
    if process is None:
        return
    if os.name == "nt":
        if process.poll() is not None:
            return
        result = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                capture_output=True, timeout=10, creationflags=FLAGS)
        if result.returncode and process.poll() is None:
            process.kill()
        process.wait(timeout=5)
        return
    # The group outlives an exited leader while grandchildren remain; the kernel does
    # not reuse a PID that is still a live process group id.
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
                break
            time.sleep(0.05)
        else:
            continue
        break
    if process.poll() is None:
        process.kill()
    process.wait(timeout=5)


# Windows mutexes are recursive for their owning thread; reject nested API use too.
_active = set()
_active_guard = threading.Lock()


def probe_identity(serial, backend="openocd", family=None):
    """Hash of family:SERIAL; OpenOCD and the ST server share the ST-Link family.

    `family` names the probe when the stand selects another OpenOCD interface (`probes.family`).
    """
    if backend not in ("openocd", "stlink", "jlink", "st-util"):
        raise ValueError("Unknown debugger backend")
    if not isinstance(serial, str) or not re.fullmatch(r"[A-Za-z0-9]+", serial):
        raise ValueError("Explicit alphanumeric debugger serial required")
    family = family or ("jlink" if backend == "jlink" else "stlink")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", family):
        raise ValueError("Invalid debugger probe family")
    identity = family + ":" + serial.upper()
    return hashlib.sha256(identity.encode("ascii")).hexdigest()


def probe_mutex_name(serial, backend="openocd", family=None):
    return "Local\\stm32-gdbtest.probe.v1." + probe_identity(serial, backend, family)


def lock_directory():
    """Host-wide directory shared by runners of every checkout and user."""
    return Path(os.environ.get("STM32_GDBTEST_LOCK_DIR") or tempfile.gettempdir()) / "stm32-gdbtest-locks"


def probe_lock_path(serial, backend="openocd", family=None):
    return lock_directory() / ("probe.v1." + probe_identity(serial, backend, family) + ".lock")


def _kernel_api():
    from ctypes import wintypes
    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    api.CreateMutexW.restype = wintypes.HANDLE
    api.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    api.WaitForSingleObject.restype = wintypes.DWORD
    api.ReleaseMutex.argtypes = [wintypes.HANDLE]
    api.ReleaseMutex.restype = wintypes.BOOL
    api.CloseHandle.argtypes = [wintypes.HANDLE]
    api.CloseHandle.restype = wintypes.BOOL
    return api


@contextmanager
def probe_lock(root, serial, backend="openocd", family=None):
    if os.name == "nt":
        with _windows_probe_lock(root, serial, backend, family):
            yield
    else:
        with _posix_probe_lock(serial, backend, family):
            yield


@contextmanager
def _claim(name):
    with _active_guard:
        if name in _active:
            raise RuntimeError("Debugger already owned by a runner in this process")
        _active.add(name)
    try:
        yield
    finally:
        with _active_guard:
            _active.remove(name)


@contextmanager
def _posix_probe_lock(serial, backend, family=None):
    """Fail-fast ownership on one host through flock in a shared directory.

    The kernel drops flock when the owner dies; the owner record left in the file
    then marks abandoned ownership, as WAIT_ABANDONED does on Windows. It coordinates
    participating runners only and does not prove that server children terminated.
    """
    import fcntl
    path = probe_lock_path(serial, backend, family)
    with _claim(path.name):
        directory = path.parent
        try:
            directory.mkdir(parents=True, exist_ok=True)
            if directory.stat().st_uid == os.getuid():
                directory.chmod(0o1777)  # Shared by users; sticky bit protects foreign files.
        except OSError as exc:
            raise RuntimeError(f"Debugger lock directory unavailable: {directory}") from exc
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o666)
        try:
            if os.fstat(descriptor).st_uid == os.getuid():
                os.fchmod(descriptor, 0o666)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in (errno.EWOULDBLOCK, errno.EACCES):
                    raise RuntimeError("Debugger already owned by another runner on this host") from exc
                raise
            try:
                previous = os.pread(descriptor, 256, 0)
                if previous.strip():
                    os.ftruncate(descriptor, 0)  # Explicit retry after the check is accepted.
                    raise RuntimeError("Abandoned debugger ownership: check orphan GDB/server processes "
                                       "before retry (" + previous.decode("ascii", "replace").strip() + ")")
                os.pwrite(descriptor, f"pid={os.getpid()}\n".encode("ascii"), 0)
                try:
                    yield
                finally:
                    os.ftruncate(descriptor, 0)
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


@contextmanager
def _windows_probe_lock(root, serial, backend="openocd", family=None):
    """Fail-fast ownership within one Windows session; also retain legacy local lock.

    This coordinates participating runners, not arbitrary vendor tools. Release of
    a dead owner's mutex does not prove that its debug-server children terminated.
    """
    import msvcrt
    name = probe_mutex_name(serial, backend, family)
    with _active_guard:
        if name in _active:
            raise RuntimeError("Debugger already owned by a runner in this process")
        _active.add(name)
    handle = None
    owned = False
    try:
        api = _kernel_api()
        handle = api.CreateMutexW(None, False, name)
        if not handle:
            raise ctypes.WinError(ctypes.get_last_error())
        state = api.WaitForSingleObject(handle, 0)
        owned = state in (0, 0x80)  # WAIT_OBJECT_0 / WAIT_ABANDONED both grant ownership.
        if state == 0x102:
            raise RuntimeError("Debugger already owned by another runner in this Windows session")
        if state == 0x80:
            raise RuntimeError("Abandoned debugger ownership: check orphan GDB/server processes before retry")
        if state != 0:
            raise ctypes.WinError(ctypes.get_last_error())
        # Preserve exclusion with older runners in the same checkout during migration.
        directory = Path(root) / "build/probe-locks"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / (hashlib.sha256(serial.encode()).hexdigest() + ".lock")
        with path.open("a+b") as lock:
            try:
                if os.fstat(lock.fileno()).st_size == 0:
                    lock.write(b"0")
                    lock.flush()
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise RuntimeError("Debugger already owned by a legacy runner in this checkout") from exc
            try:
                yield
            finally:
                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        try:
            if handle:
                try:
                    if owned and not api.ReleaseMutex(handle):
                        raise ctypes.WinError(ctypes.get_last_error())
                finally:
                    if not api.CloseHandle(handle):
                        raise ctypes.WinError(ctypes.get_last_error())
        finally:
            with _active_guard:
                _active.remove(name)
