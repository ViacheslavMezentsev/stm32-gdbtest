"""Bounded process lifetime and cross-project debugger ownership on Windows."""

from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import os
from pathlib import Path
import subprocess
import threading
import re


FLAGS = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def stop_tree(process):
    if process is None or process.poll() is not None:
        return
    result = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                            capture_output=True, timeout=10, creationflags=FLAGS)
    if result.returncode and process.poll() is None:
        process.kill()
    process.wait(timeout=5)


# Windows mutexes are recursive for their owning thread; reject nested API use too.
_active = set()
_active_guard = threading.Lock()


def probe_mutex_name(serial, backend="openocd"):
    if backend not in ("openocd", "stlink", "jlink"):
        raise ValueError("Unknown debugger backend")
    if not isinstance(serial, str) or not re.fullmatch(r"[A-Za-z0-9]+", serial):
        raise ValueError("Explicit alphanumeric debugger serial required")
    family = "jlink" if backend == "jlink" else "stlink"
    identity = family + ":" + serial.upper()
    return "Local\\stm32-gdbtest.probe.v1." + hashlib.sha256(identity.encode("ascii")).hexdigest()


def _kernel_api():
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
def probe_lock(root, serial, backend="openocd"):
    """Fail-fast ownership within one Windows session; also retain legacy local lock.

    This coordinates participating runners, not arbitrary vendor tools. Release of
    a dead owner's mutex does not prove that its debug-server children terminated.
    """
    import msvcrt
    name = probe_mutex_name(serial, backend)
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
