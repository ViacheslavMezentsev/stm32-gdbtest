# J-Link GDB Server

[Backend](index.md) · [Русский](../../ru/backends/jlink.md)

Shared session files and stand options: [TOML map](../BACKENDS.md#toml). Target fragments extend a complete MCU profile.

## Configuration

`jlink` uses SEGGER J-Link GDB Server on Windows/Linux, including the arm64 stands used here.
SEGGER device support is not module acceptance: verified versions/MCUs are in the [matrix](../API_ACCEPTANCE.md).

```toml
[probe]
backend = "jlink"
serial = "REPLACE_WITH_JLINK_SERIAL"
executable = "C:/Program Files/SEGGER/JLink/JLinkGDBServerCL.exe"
speed_khz = 1000
flash = "if-different"
```

[Template](../../../tests/firmware/stands/jlink.example.toml).

Linux name: `JLinkGDBServerCLExe`. Serial is a decimal USB number, not an index or nickname.
`interface` accepts SWD/JTAG; acceptance concerns a specific connection. Target schema 2 fragment:

```toml
jlink_device = "STM32F103CB"

[jlink]
reset_halt = "monitor reset"
```

`jlink_device` is a top-level key before TOML sections. Without it the map covers
STM32F103C8T6→STM32F103C8, STM32F103CBT6→STM32F103CB, STM32F030R8T6→STM32F030R8.
Other MCUs need an explicit name and separate validation, not automatic string truncation.

## Lifecycle

Runner sets `-device`, `-USB`, `-if`, `-speed`, GDB port; disables SWO/Telnet/RTT;
enables localhost-only, nogui, strict and multiple connections. `-noreset`, `-nohalt`, `-noir`
do not replace scenario reset. Readiness: `Waiting for GDB connection`.
After extended-remote, `monitor flash breakpoints = 0` selects hardware breakpoints.
Reset/halt: `monitor reset`. Finish/recovery: `monitor reset`, `monitor go`, `disconnect`.
`[jlink].reset_run` is unsupported. Logs: `jlink.log`, `server.log`, `gdb.log`.

## Details that affected integration

- WeAct BluePill-Plus needed a separate CB mapping: the profile MCU name differs from SEGGER's name.
- Embedded J-Link STLink on Nucleo requested a terms window and missed readiness without confirmation.
  `-nogui` does not guarantee absence of such windows. The owner performs initial setup; increasing
  `startup_timeout_s` (1…120s) cannot answer the window.
- USB-open hangs before MCU access are not firmware FAIL. Save logs and check J-Link accessibility;
  debugger firmware is not updated automatically. See [HOWTO](../HOWTO.md).
- Over SSH the actual server exit is checked, not merely helper success. Requested SIGTERM after EOF
  is allowed; crashes/SIGKILL remain ERROR.

[SEGGER documentation](https://kb.segger.com/J-Link_GDB_Server).
