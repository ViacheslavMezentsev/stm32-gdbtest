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

## Step by step: attach your own compatible MCU

The procedure for a consumer project; attaching the module and the first scenario follow
[getting started](GETTING_STARTED.md). Take the values from the chip's RM and datasheet, not from the STM32 analogue.

1. **The debugger sees the chip.** Connect without the module. J-Link Commander:
   `JLink.exe -device <name> -if SWD -speed 4000 -autoconnect 1` (Linux: `JLinkExe`); the device name comes from the
   SEGGER supported device list or the device selection dialog. If J-Link does not know the chip, the core name
   (`Cortex-M4`) connects, but Flash programming is then usually unavailable: use the vendor OpenOCD. For OpenOCD:
   `openocd -f interface/<probe>.cfg -f target/<target>.cfg`, then `telnet localhost 4444`.
2. **Three RM values, read on the board.** Read them in the same session (`mem32 <address> 1` in J-Link Commander,
   `mdw <address>` in OpenOCD, `x/wx <address>` in GDB) and compare with the RM:
   - the chip identifier (`0xE0042000` on STM32 and many compatibles) → `[identity]` `address`, `mask`, `value`;
     the mask keeps only the bits the RM calls the identifier;
   - the factory Flash size in KiB (the low 16 bits of the word) → `flash_size_address`; without such a register the hardware run is
     refused, so the module does not fit that MCU yet;
   - `FP_CTRL` (`0xE0002000`): FPB code comparators = `NUM_CODE` (bits 14:12 high, 7:4 low) → `breakpoint_limit`.
3. **Profile.** Copy the STM32 profile of the same core (Cortex-M0 — `f030r8`, M3 — `f103c8`, M4 — `f411ce` or
   `at32f403a`) and replace `mcu`, `name`, `flash_start`, `flash_size`, the step 2 fields, `jlink_device` or
   `openocd_target`. `fault_handlers`, `core_registers` and `[diagnostic_registers]` match the core of the same class
   when the firmware vector table uses the same handler names.
4. **Stand.** The server and the probe go to the stand file (`*.local.toml` or `<profile>-<server>.remote.toml`, not
   in git). For J-Link the stand does not change; for the vendor OpenOCD set its `executable`, and for another probe
   `interface` and `transport` ([GDB servers](BACKENDS.md)).
5. **Build with the vendor CMSIS.** The linker script and startup come from the vendor or follow its memory map; keep
   the SDK outside the repository and pass its path through a CMake or environment variable, like `AT32_SDK_ROOT` in
   the check firmware.
6. **Without the board.** `python -B -m stm32_gdbtest doctor --stand <stand>`, then `run --prepare-only` of the first
   scenario: it checks the profile, the stand, the manifest and the ELF.
7. **On the board.** Start with a smoke scenario: `boot()`, reaching `main`, reading one peripheral register with a
   known reset value. On an identity error compare the value read with the RM: usually the mask or the address is
   wrong. Then the peripheral scenarios by the rules of the "Scenarios" section, and several runs in a row to filter out
   stand instability.

## Not validated

Other families of compatible MCUs, vendor OpenOCD builds and probes such as WCH-Link in ARM mode — each needs its
own board acceptance.
