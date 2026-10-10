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
| `backend` | `openocd`, `stlink` (ST-LINK GDB Server), `st-util` or `jlink` |
| `serial` | Explicit debugger serial number; for J-Link the decimal USB number |
| `executable` | Server: a name on PATH or an absolute path; defaults `openocd`, `ST-LINK_gdbserver(.exe)`, `st-util(.exe)`, `JLinkGDBServerCL.exe` (Windows) or `JLinkGDBServerCLExe` (Linux) |
| `speed_khz` | 1…4000, default 1000 — an upper limit, not the actual interface frequency |
| `flash` | `if-different` (default) or `verify-only` |
| `[remote]` | A separate table: the GDB server on a Linux stand host over SSH ([Linux stand](LINUX_STAND.md#remote-gdb-server-windows-or-wsl--orange-pi)); `executable` and `programmer_dir` then refer to the stand host |
| `startup_timeout_s` | 1…120, default 10 — how long to wait for the server to become ready; probes with a slow target connection need more |
| `programmer_dir` | `stlink` only: absolute directory containing `STM32_Programmer_CLI.exe` (without `.exe` on Linux) |
| `interface` | `openocd`: the interface script, default `interface/stlink.cfg`; `jlink`: `SWD` (default) or `JTAG` |
| `transport` | `openocd` only: `transport select …` after the interface script (`swd`, `jtag`, `hla_swd`, `hla_jtag`, `dapdirect_swd`, `dapdirect_jtag`, `sdi`); not set by default |

Unknown keys are rejected. Templates: [OpenOCD](../../examples/stands/stlink.example.toml)
and [OpenOCD, ST, st-util, J-Link for the CI firmware](../../tests/firmware/stands/jlink.example.toml)
(`openocd.example.toml`, `stlink.example.toml`, `st-util.example.toml` and `remote.example.toml` for a remote stand
in the same folder). Local paths (`executable`, `programmer_dir`, `identity_file`) expand `~`,
`%VAR%` and `$VAR`: `%USERPROFILE%/...` instead of a personal path. Local paths
and serial numbers are not committed: local stands are `<profile>-<backend>.local.toml`, remote ones
`<profile>-<backend>.remote.toml`, both ignored by Git. `run --prepare-only --stand …`
validates the stand and backend commands without connecting to the debugger, and
`doctor --stand …` also checks GDB-Python, OpenOCD/st-util and USB access.

A `target.toml` profile may name the J-Link device with the `jlink_device` key (for example for an MCU outside
the validated STM32 parts); without it the validated STM32 table is used.
A schema 2 profile keeps the dialect of each server in a section named after the backend
(`[openocd]`, `[jlink]`, `[stlink]`, `[st-util]`); `reset_halt = "monitor reset init"` in `[openocd]`
is a reset with the target init procedure. An absent section means the built-in dialect.
Probe locks distinguish families: another OpenOCD interface script does not share the lock of an ST-Link with the same serial.

On Linux ST-LINK GDB Server (STM32CubeCLT) exists for x86_64 only; on aarch64
(Orange Pi 5) use OpenOCD, J-Link or the verified st-util build. OpenOCD 0.10 from the Ubuntu 20.04 repository
lacks `interface/stlink.cfg`, so the stand environment installs xPack OpenOCD 0.12.0-7.
This build warns about the deprecated `tcl_port`/`telnet_port`/`gdb_port`; the
commands stay compatible with OpenOCD 0.12.0.

## TOML

| File | Purpose | Backend relationship |
| --- | --- | --- |
| `session.toml` | Session configuration; `[config]` paths are relative to its directory | Does not select a server executable |
| `target.toml` | MCU, memory, identity and schema 2 dialects | Optional `[openocd]`, `[stlink]`, `[jlink]`, `[st-util]` sections |
| `api.toml` | Scenario API settings and user data | Old `reset.command` was removed; no server commands here |
| `full_image.toml` | Optional full-image policy | Same image checks for all backends; see [images](IMAGES.md) |
| `<profile>-<backend>.local.toml` / `.remote.toml` | `[probe]` selects server, serial and options; `[remote]` enables SSH | Local untracked stand file selected by `--stand` or the precedence above |
| `session.json` | Generated runner inputs, ELF and build | Does not replace user session.toml; not edited manually |

```toml
# session.toml; these are file references, not backend commands.
[config]
target = "target.toml"
api = "api.toml"
image = "full_image.toml" # Optional; omit when not using a full-image policy.
```

Complete `SESSION_CONFIG` integration, session.json generation and CLI: [API](API.md).
The stand selects the backend, not the target profile. Target sections on individual pages are
fragments of a complete profile, not standalone target.toml files. Only OpenOCD accepts `reset_run`;
other finish sequences belong to the backend. One-off `STM32_GDBTEST_RESET_COMMAND` changes reset/halt,
not recovery; it is not a replacement for portable profile configuration.

## Verified differences

| Backend / details | Readiness | Default reset/halt | Finish and recovery |
| --- | --- | --- | --- |
| [OpenOCD](backends/openocd.md) | Listening on port … for gdb connections | `monitor reset halt` | `monitor reset run`, `disconnect` |
| [ST-LINK GDB Server](backends/stlink.md) | Waiting for debugger connection | `monitor reset` | `monitor reset`, `detach` |
| [J-Link](backends/jlink.md) | Waiting for GDB connection | `monitor reset` | `monitor reset`, `monitor go`, `disconnect` |
| [st-util](backends/st-util.md) | Listening at *:PORT… (ASCII `...`) | `monitor reset` | `monitor reset`, `monitor resume`, `disconnect` |

All use `target extended-remote`. Schema 1 remains compatible: top-level reset fields apply only
to OpenOCD. Schema versions and migration: [API](API.md).

## Server specifics

Individual pages cover TOML, dependencies, startup/shutdown, fixes and limits. The st-util page also
covers 1.6.0/1.9.0 results and building 1.9.0 with private libusb on Ubuntu 20.04.
Acceptance is version/stand-specific: [matrix](API_ACCEPTANCE.md).

## Limits and extension

A vendor server may access SWD on startup before GDB. `prepare-only` does not start a server;
doctor success does not establish MCU or scenario correctness. New backend acceptance covers
programming/verify-only, timeout/recovery, shutdown and final MCU state. Do not copy monitor commands
by analogy. Mass erase, option bytes, debugger firmware updates and shared mode are not enabled automatically.
Observation without halt, SWV, external loaders, multicore and authentication are outside the verified common API.
[Ownership](DEBUGGER_OWNERSHIP.md) · [Linux/SSH](LINUX_STAND.md) · [HOWTO](HOWTO.md).

## st-util (v0.4.0)

Details moved to the [st-util page](backends/st-util.md), including version differences, Ubuntu 20.04
build, Listening/idle waits and actual server exit.
