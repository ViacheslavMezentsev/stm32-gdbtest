# Cortex-M compatible MCUs from other vendors

[Documentation](index.md) → Compatible MCUs · [Русский](../ru/COMPATIBLE_MCU.md)

The module checks firmware through GDB-Python and does not depend on the MCU vendor as long as the core is
Cortex-M and the GDB server can connect to the chip. Clones and compatible MCUs (Artery AT32, GigaDevice GD32,
Geehy APM32 and so on) are attached with their own `target.toml` profile and the vendor CMSIS; the module core does
not change. The validated example is the `at32f403a` profile of the check firmware: WeAct AT32F4 Core Board
(AT32F403ACGU7), J-Link, 44 scenarios.

## Profile

| Field | What to set | AT32F403ACGU7 |
| --- | --- | --- |
| `mcu`, `name` | chip marking and profile name | `AT32F403ACGU7`, `ciat32f403a` |
| `[identity]` | address, mask and value of the identifier from the RM. Any width: the 12-bit STM32 DEV_ID, the 32-bit Artery PID | `0xE0042000`, `0xFFFFFFFF`, `0x70050347` (RM 27.4.1) |
| `flash_size_address` | the 16-bit factory Flash size register in KiB (a hardware run is refused without it) | `0x1FFFF7E0` (RM 1.3) |
| `breakpoint_limit` | number of FPB code comparators | 6 |
| `fault_handlers`, `core_registers`, `[diagnostic_registers]` | as for a Cortex-M core of the same class | as for STM32F4 |
| `jlink_device` | the J-Link device name when the server is J-Link | `AT32F403ACGU7` |
| `openocd_target` | the OpenOCD script; many compatible MCUs have it only in the vendor's OpenOCD | `target/at32f403axx.cfg` |

A J-Link stand does not change; `interface = "JTAG"` in `[probe]` is needed only for chips without SWD. For OpenOCD
with another probe the stand sets `interface` (an `interface/*.cfg` script) and, if needed, `transport`
([GDB servers](BACKENDS.md)).

## Vendor CMSIS

The firmware is built with the vendor headers instead of STM32Cube. The SDK is not copied into the repository: the
check firmware reads it from `AT32_SDK_ROOT`. In CI the archive is pinned in `ci/dependencies.lock.json` (URL and
SHA-256), and only `libraries/cmsis` and `libraries/drivers/inc` are extracted. On a workstation the same archive
is installed by

```powershell
python tools/vendor_sdk.py
```

into `%USERPROFILE%/Artery/<package>` (Linux: `/opt/Artery/<package>`), where CMake looks for it by default;
another place is `--destination` plus the `AT32_SDK_ROOT` variable. The build manifest records the Artery package
like STM32Cube.

## Scenarios

- The shared module scenarios (navigation, `ret`, `watch`, `call`, measurements) run unchanged.
- Peripheral scenarios are written anew: register and macro names differ between vendors. The Artery SDK describes
  registers as bit fields, and GDB expressions read them directly: `GPIOC->odt_bit.odt13`, `CRM->ctrl_bit.hicken`.
- A whole register value is compared with a constant built from the RM bit positions, not with firmware masks.
- Write-only registers read as zero. On AT32F403A these are `RTC_DIV` and `RTC_TA`: check them through the readable
  `RTC_DIVCNT` and `RTC_CNT`. On STM32F103 the same registers are write-only in the RM too, although they read back
  on the board; do not rely on that.
- Conversion constants (temperature sensor) come from the vendor datasheet or example; the source is marked by the
  quality code of the result (`adc_units.c`: 4 — vendor example constants).

## Not validated

Other families of compatible MCUs, vendor OpenOCD builds and probes such as WCH-Link in ARM mode — each needs its
own board acceptance.
