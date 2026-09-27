# Debugger ownership across projects

[Documentation](index.md) → Debugger ownership · [Русский](../ru/DEBUGGER_OWNERSHIP.md)

## Mechanism

`probe_lock(root, serial, backend="openocd")` uses the named Windows mutex
`Local\stm32-gdbtest.probe.v1.<sha256>`. The key is the debugger family and the
upper-case serial number: OpenOCD and the ST server map to `stlink`, J-Link to
`jlink`. The project root, MCU and GDB port are not part of the key. The serial number
is not published in the object name, but the hash is not a way to hide secrets.

The coordination scope is **one Windows session**: different processes, projects and
module copies that use this protocol. The `Local` namespace does not cover another
session, RDP or services. The object lives in the OS kernel; no files are created
outside the project. API and recursive ownership semantics —
[CreateMutexW](https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-createmutexw),
the session boundary — [Kernel object namespaces](https://learn.microsoft.com/en-us/windows/win32/termserv/kernel-object-namespaces).

The lock is taken without waiting — after reading the stand and profile, before the
ELF snapshot, preflight, `objcopy` and the server start. A busy mutex gives ERROR with
JSON/JUnit and no hardware connection. The lock is held for the whole run, including
recovery and stopping the server process tree. An external tool that uses the
debugger must take part in the same protocol. An in-process guard rejects a nested
acquisition, because a Windows mutex is recursive for its owning thread. One import
of the package per Python process is supported.

`run --prepare-only` does not access the debugger and takes no lock.

The older file lock `build/probe-locks/<sha256(serial)>.lock` is held inside the
mutex for compatibility with an old runner in the same checkout. Therefore two
debuggers of different families with the same serial number in one checkout may
be refused conservatively. An old runner in another checkout does not know the new
mutex — update all participating projects. Vendor tools, VS Code and an arbitrary
OpenOCD or GDB server do not use the protocol and are not blocked by it.

## Exit and failures

Normal exit and a Python exception release the file lock, the mutex and the handle
in `finally`. An API or permission error never bypasses the lock. When a process
ends, Windows releases its mutex — this is **not proof that child servers exited**.

`WAIT_ABANDONED` means ownership was obtained after the previous owner died. The
runner releases the object and refuses before connecting, suggesting to check
leftover GDB and server processes. This is not a lasting quarantine: once all handles
are closed the object disappears and the next run will not know about the crash.
Killing foreign processes or resetting the MCU because of this state is not allowed.
After a host crash first check and stop leftover servers. Child process supervision
(Job Object) is a separate task ([roadmap](../../TODO.md), Russian).

## Checking the mechanism

Host tests: `Tests/host/test_probe_lock.py`; they run on Windows only (in CI — the
`windows-2022` job). Hardware results and process contention experiments are
[in the stand project](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/DEBUGGER_OWNERSHIP.md) (Russian).
