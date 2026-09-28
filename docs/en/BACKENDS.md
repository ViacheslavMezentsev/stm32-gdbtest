# GDB servers (backends)

[Documentation](index.md) → GDB servers · [Русский](../ru/BACKENDS.md)

A backend defines server start and readiness, setup, reset, finish and recovery
commands. Scenarios use the common Target API; peripheral expectations stay with the
consumer. The stand is selected by `--stand` → `STM32_GDBTEST_STAND` → `session.stand`
([API](API.md)). Hardware runs are supported on Windows and Linux
([Linux stand](LINUX_STAND.md)).

## Stand

The `[probe]` table of the local TOML:

| Key | Value |
| --- | --- |
| `backend` | `openocd`, `stlink` (ST-LINK GDB Server) or `jlink` |
| `serial` | Explicit debugger serial number; for J-Link the decimal USB number |
| `executable` | Server: a name on PATH or an absolute path; defaults `openocd`, `ST-LINK_gdbserver(.exe)`, `JLinkGDBServerCL.exe` (Windows) or `JLinkGDBServerCLExe` (Linux) |
| `speed_khz` | 1…4000, default 1000 — an upper limit, not the actual interface frequency |
| `flash` | `if-different` (default) or `verify-only` |
| `startup_timeout_s` | 1…120, default 10 — how long to wait for the server to become ready; probes with a slow target connection need more |
| `programmer_dir` | `stlink` only: absolute directory containing `STM32_Programmer_CLI.exe` (without `.exe` on Linux) |

Unknown keys are rejected. Templates: [OpenOCD](../../examples/stands/stlink.example.toml)
and [OpenOCD, ST, J-Link for the CI firmware](../../Tests/firmware/stands/jlink.example.toml)
(`openocd.example.toml` and `stlink.example.toml` in the same folder). Local paths
and serial numbers are not committed (`*.local.toml`). `run --prepare-only --stand …`
validates the stand and backend commands without connecting to the debugger, and
`doctor --stand …` also checks GDB-Python, OpenOCD and USB access.

On Linux ST-LINK GDB Server (STM32CubeCLT) exists for x86_64 only; on aarch64
(Orange Pi 5) use OpenOCD and J-Link. OpenOCD 0.10 from the Ubuntu 20.04 repository
lacks `interface/stlink.cfg`, so the stand environment installs xPack OpenOCD 0.12.0-7.
This build warns about the deprecated `tcl_port`/`telnet_port`/`gdb_port`; the
commands stay compatible with OpenOCD 0.12.0.

## Verified differences

| Operation | OpenOCD 0.12.0 | ST-LINK GDB Server 7.14.0 (CubeCLT 1.22.0) | J-Link GDB Server 8.32 |
| --- | --- | --- | --- |
| MCU selection | Profile `openocd_target` | Detected by the ST server; runner identity check kept | MCU → J-Link device mapping |
| Start | `interface/stlink.cfg` + target, localhost | SWD, attach `-g`, persistent `-e`, serial, CubeProgrammer path | SWD, `-USB <serial>`, localhost, no SWO/Telnet/RTT |
| Readiness | `Listening on port … for gdb connections` | `Waiting for debugger connection` | `Waiting for GDB connection` |
| GDB connection | extended-remote | extended-remote | extended-remote |
| Setup | — | — | `monitor flash breakpoints = 0` |
| Reset/halt | `monitor reset halt` | `monitor reset` | `monitor reset` |
| Programming | GDB load, OpenOCD flash driver | GDB load, server calls CubeProgrammer; server-side verify `-s` | GDB load |
| Finish | `monitor reset run`, `disconnect` | `monitor reset`, `detach` | `monitor reset`, `monitor go`, `disconnect` |
| External timeout | New GDB client for recovery | New client to the persistent server: reset + detach | New client: reset + go + disconnect |
| Runtime metadata | OpenOCD version, STLINK firmware and API | Server version and firmware; API v2 is not in the banner (`null`) | Server version and J-Link firmware string |

All three backends passed the same CI firmware steps on hardware at commit
`fbc103d`, including the full image and timeout with recovery ([status](STATUS.md)).

Target schema 1 is kept for compatibility: the `openocd_target`, `reset_halt` and
`reset_run` fields are used only by OpenOCD. ST and J-Link take their commands from
the backend, while identity, Flash bounds, breakpoints and fault handlers come from
the common profile. This is transitional compatibility, not a universal profile schema.

## Server specifics

**ST-LINK GDB Server** opens the SWD connection itself before the GDB client starts:
the GDB API check before connecting does not mean the debugger was not accessed.
Attach does not mean the debugger has no influence. With 1000 kHz requested the
server reported a COM frequency of 950 kHz. The extra SWV port (observed as GDB
port + 1) is not used; the CLI help has no equivalent of OpenOCD `bindto`, so the
processes are meant for a local stand. Shared mode `-t` is not used: both ST
backends are protected by one lock per serial number and the server belongs to the
run. Logs and temporary files (`--temp-path`, `-f`, `TEMP`/`TMP`) go to the
consumer's run directory; the process tree is closed at the end.

**J-Link.** Verified mappings: `STM32F103C8T6` → `STM32F103C8` (J-Link CE) and
`STM32F030R8T6` → `STM32F030R8` (on-board J-Link STLink on Nucleo). Other MCUs are
rejected before the server starts until a mapping is verified. Flash breakpoints are
disabled; hardware breakpoints are used.

## Limits and extension

- A vendor server may access SWD already at start. The offline ELF check runs before
  the server, but the GDB API presence check does not mean there was no hardware access.
- monitor/detach commands must not be carried over between servers by analogy. A new
  backend or mapping needs hardware checks of programming, verify-only,
  timeout/recovery and the final MCU state.
- Mass erase, option bytes, debugger firmware updates and shared mode are never
  enabled automatically. Locking — [debugger ownership](DEBUGGER_OWNERSHIP.md).
- Observation without halt, SWV, external loaders, multicore and authentication are
  not part of the proven common API; `observe_sleep` and Commander experiments are
  tools of the stand project.

[Stand commands and results](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/GDB_BACKENDS.md),
[J-Link experiments](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/main/docs/JLINK.md) (Russian).
