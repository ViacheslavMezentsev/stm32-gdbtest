# Debugger ownership across projects

[Documentation](index.md) → Debugger ownership · [Русский](../ru/DEBUGGER_OWNERSHIP.md)

## Mechanism

`probe_lock(root, serial, backend="openocd")` uses the named mutex
`Local\stm32-gdbtest.probe.v1.<sha256>` on Windows and a file with `flock` on Linux
(see [Linux](#linux)). The key is the debugger family and the
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

`run --prepare-only` and `doctor` do not access the debugger and take no lock.

The older file lock `build/probe-locks/<sha256(serial)>.lock` (Windows only) is held
inside the mutex for compatibility with an old runner in the same checkout. Therefore two
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

## Linux

The lock is the file `probe.v1.<sha256>.lock` with the same hash in the
`stm32-gdbtest-locks` directory under `STM32_GDBTEST_LOCK_DIR`, or under `/tmp` without
the variable. It is taken with `flock` without waiting; a busy file gives the same
ERROR "another runner on this host". The directory is created with mode `1777` and
the files with `0666`, so all users and checkouts of the host share the lock.

The kernel drops `flock` when the owning process ends, so to detect a crash the owner
writes `pid=<PID>` into the file and clears it on release. If the next runner takes
the file and finds a record, the previous owner crashed: the runner clears the record
and refuses with "Abandoned debugger ownership", as with `WAIT_ABANDONED`. The next run
after the check proceeds.

The coordination scope is one kernel and one directory. A container, a virtual
machine or a WSL distribution with its own `/tmp` does not see the host lock; set a
shared directory with `STM32_GDBTEST_LOCK_DIR`. The WSL lock does not interact with the
Windows mutex: do not use one debugger from Windows and WSL at the same time.

The server and GDB start in their own process group. Stopping sends `SIGTERM` to the
group and `SIGKILL` after 3 s, so children of the server end too, even if the leader
has already exited. A crash of the runner itself does not stop the group — check
leftover processes (`pgrep -a openocd`, `pgrep -a JLink`).

## Remote stand

A stand with `[remote]` has two locks: one on the runner's computer (a mutex on
Windows, `flock` on Linux) and an `flock` on the stand host with the same hash. The
helper script takes the second one before starting the server, so a run from Windows
and a local run on the Orange Pi never use one debugger at the same time. Stand host
refusals come as "Stand host refused the run: busy / abandoned". When the SSH session
closes or breaks, the helper stops the server and releases the lock; when the link is
lost without closing the connection (Wi-Fi, cable, a sleeping computer), this happens
after 15 s without the runner's heartbeat
([Linux stand](LINUX_STAND.md#remote-gdb-server-windows-or-wsl--orange-pi)).

## Checking the mechanism

Host tests: `Tests/host/test_probe_lock.py`. The Windows part runs on Windows (in CI —
the `windows-2022` job), the Linux part (lock, abandoned ownership, stopping the
process group) on Linux. The stand host lock and the remote server helper are tested by
`Tests/host/test_remote.py` (`RemoteHelperTests`, Linux). Hardware results and process contention experiments are
[in the stand project](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/DEBUGGER_OWNERSHIP.md) (Russian).
