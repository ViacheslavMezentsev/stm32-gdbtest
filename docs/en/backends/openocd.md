# OpenOCD

[Backend](index.md) · [Русский](../../ru/backends/openocd.md)

Shared session files and stand options: [TOML map](../BACKENDS.md#toml). Target fragments extend a complete MCU profile.

## Configuration

`openocd` uses OpenOCD 0.12.0/xPack 0.12.0-7 in verified Windows/Linux configurations.
Ubuntu 20.04 OpenOCD 0.10 lacks the selected `interface/stlink.cfg`; the
[Linux stand environment](../LINUX_STAND.md) installs xPack.

```toml
[probe]
backend = "openocd"
serial = "REPLACE_WITH_STLINK_SERIAL"
executable = "openocd"
speed_khz = 1000
flash = "if-different"
```

[Template](../../../tests/firmware/stands/openocd.example.toml).

`interface` selects the debugger script; optional `transport` runs after it. Check available
transports before copying settings from another build. The MCU profile contains `openocd_target`,
for example `target/stm32f4x.cfg`. Target schema 2 fragment:

```toml
[openocd]
reset_halt = "monitor reset halt"
reset_run = "monitor reset run"
```

`monitor reset init` is also allowed for a target with an initialization procedure. Without this section,
the defaults above apply. [Complete F411 target](../../../tests/firmware/profiles/f411ce/target.toml).

## Startup and shutdown

Runner passes interface/target, `adapter serial`, `adapter speed`, a dedicated GDB port and
`bindto 127.0.0.1`; Tcl/Telnet are disabled. Readiness: `Listening on port … for gdb connections`.
GDB uses extended-remote. Reset/halt precedes checks; `load` uses the OpenOCD Flash driver under
`if-different`. Finish: `monitor reset run`, `disconnect`. A new client performs recovery after timeout;
reset/halt overrides do not change that sequence.

## Details and fixes

- Schema 1→2 moved commands into `[openocd]`. Legacy top-level fields still apply only to OpenOCD,
  including `monitor reset init`.
- Standard ST-Link shares its lock with `stlink` and `st-util`. Other interface families have different
  lock identities; this is not a universal adapter lock.
- xPack warns about deprecated `gdb_port`, `tcl_port`, `telnet_port`; syntax retains 0.12.0 compatibility.
  Actual SWD speed may be below the request.
- Over SSH, exit `-15` is allowed only for helper-requested SIGTERM after EOF. Crashes, SIGKILL and
  missing confirmation remain ERROR.
- F429 once reported invalid SP and a read at `0x20030020`. Subsequent campaigns did not reproduce it;
  cause unknown. Inspect `server.log`/`gdb.log`, not just `result.warnings`.

OpenOCD restored BOOT/GPIO after other servers failed. Inaccessible USB first requires restored access
to the debugger itself. [Matrix and limits](../../evidence/en/API_ACCEPTANCE.md).

## Graceful local OpenOCD/J-Link shutdown

For `backend = "openocd"`, `interface = "interface/jlink.cfg"` without SSH, the runner
arms `gdb-detach {shutdown}` after `reset_run`, then executes `disconnect`.
OpenOCD exits normally and releases its J-Link registration instead of being killed
immediately. The detach event is not overridden before finish, retaining the existing
host recovery route after an early GDB failure. Host recovery uses the same finish sequence.

The runner waits up to 3 seconds for its server to exit. `server_shutdown.status = VERIFIED`
means exit 0; a nonzero exit or timeout produces ERROR and `cleanup_error`. On timeout,
the remaining owned process is forcibly terminated, recorded in `server_shutdown.forced`.
The original verdict remains in `status_before_cleanup`. Server shutdown does not prove
MCU memory restoration. USB loss may require reconnecting the probe and separate recovery.

No TOML or scenario migration is required; a shutdown wrapper target is no longer needed.
ST-Link, SEGGER GDB Server and SSH keep their existing lifecycle. This route overrides the
selected target's gdb-detach event only during finish; do not put required custom actions
in that event in your target script.
