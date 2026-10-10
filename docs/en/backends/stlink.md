# ST-LINK GDB Server

[Backend](index.md) · [Русский](../../ru/backends/stlink.md)

Shared session files and stand options: [TOML map](../BACKENDS.md#toml). Target fragments extend a complete MCU profile.

## Configuration

`stlink` selects ST's server from STM32CubeCLT, not open-source `st-util`. Programming needs
STM32CubeProgrammer. ST-LINK GDB Server 7.14.0 (CubeCLT 1.22.0) and 7.9.0 were checked on Windows.
The selected CubeCLT Linux build is x86_64; use OpenOCD or st-util on OrangePi/aarch64.

```toml
[probe]
backend = "stlink"
serial = "REPLACE_WITH_STLINK_SERIAL"
executable = "C:/ST/STM32CubeCLT/STLink-gdb-server/bin/ST-LINK_gdbserver.exe"
programmer_dir = "C:/ST/STM32CubeCLT/STM32CubeProgrammer/bin"
speed_khz = 1000
flash = "if-different"
```

[Template](../../../tests/firmware/stands/stlink.example.toml).

`programmer_dir` is an absolute directory containing `STM32_Programmer_CLI.exe`; Linux names lack `.exe`.
Over SSH both paths belong to the stand host. Target schema 2 fragment:

```toml
[stlink]
reset_halt = "monitor reset"
```

## Startup, reset and recovery

Flags include SWD `-d`, persistent `-e`, attach `-g`, serial `-i`, speed, port,
CubeProgrammer and verify `-s`. `--temp-path`, `-f`, TEMP/TMP are isolated in the run directory.
Readiness: `Waiting for debugger connection`; GDB uses extended-remote. The server can access SWD
before GDB starts; attach does not imply no MCU impact.

Finish/recovery: `monitor reset`, `detach`. Persistent accepts a new client after an external timeout.
`[stlink].reset_run` is unsupported. `monitor reset halt` is OpenOCD syntax: ST rejected it with
`Protocol error with Rcmd`. This prompted target schema 2 dialect sections and removal of the old
`api.toml reset.command`. `monitor help` lists commands for the actual server; they do not automatically
become part of the `Target.reset()` contract.

## Observed limits

- Full F411/F030 suites hit USB ERROR despite 10/10 short cycles. F411 comparisons used servers 7.14.0/7.9.0
  and GDB from xPack 13/14/15; changing the client did not remove the failure. Cause unknown;
  specification question 11.2.27 stays open. OpenOCD/st-util success does not accept this backend.
- Sometimes even OpenOCD could not open the probe until USB reconnection. Retain the original failure;
  restore BOOT/GPIO once access returns instead of automatically retrying for PASS.
- Shared mode `-t` is unused. ST-Link locks are shared with OpenOCD/st-util; the run owns its server.
- Observed 950 kHz for a 1000 request and an SWV port (GDB+1). SWV is unused; inspected help has no
  `bindto` equivalent. Account for stand network port accessibility.
- Firmware is obtained from logs; the debugger API is not guessed and can remain `null`.

[Acceptance](../API_ACCEPTANCE.md) · [ST manual](https://www.st.com/resource/en/user_manual/dm00613038-stm32cubeide-stlink-gdb-server-stmicroelectronics.pdf).
