# HAL F030: GPIO/RCC and reviewed source variants

[Documentation](index.md) · [Русский](../ru/F030_HAL_GPIO_RCC.md)

Branch `codex/f030-hal-gpio-rcc` depends on audit `4c51122`.
Extends the original 17 tests/hal-f030 cases to 22 without changing firmware.
Five techniques were adapted from consumer84a257e; this does not establish F1/F4
HAL compatibility. See the [acceptance review](CMSIS_ACCEPTANCE.md).

## New checks

| ID | Check |
| --- | --- |
| HW_GPIO_ARGUMENTS | HAL_GPIO_Init(GPIOA), PA5, output push-pull, no pull, low speed; then MODER |
| HW_GPIO_FILTERED_CALL | Conditional stop before TogglePin with PA5 High, then Low after the call |
| HW_RCC_ERROR | force_return HAL_ERROR from OscConfig → Error_Handler |
| HW_RCC_OSC_NULL | NULL OscConfig argument → real HAL_ERROR → Error_Handler |
| HW_RCC_CLOCK_NULL | NULL ClockConfig argument → real HAL_ERROR → Error_Handler |

HAL checks NULL before assertions and dereferencing. These are argument errors and
synthetic return codes, not physical oscillator failures. Cases use strict type,
enum and source-review hash contracts. [TECH-009](TESTING_TECHNIQUES.md#tech-009)
explains argument context and variant selection; TECH-004 retains force_return.

## Windows versus CI HAL

The same CubeF0 V1.11.6 directory name does not guarantee identical source.
The installed Windows RCC copy uses mutable pointers; the pinned CI copy
(HAL1.7.8) uses const pointers. Both return HAL_ERROR for NULL before assert/dereference.
Initial Linux prepare correctly reported ERROR: OscConfig types differed,
and both NULL cases rejected the source-review hash. Checks were not weakened.

configure_profile.py selects only two manually reviewed RCC SHA256 values:

| SHA256 of stm32f0xx_hal_rcc.c | RCC arguments |
| --- | --- |
| fe601fa20f95e48d4bb2a9dd7409ff4d0637e184d6b3c4be4207777b246b2856 | mutable |
| 7ddf83d26b8b9b268df2d1b3c000835360b555aa09727a4c5471e67220d43187 | const |

Selection follows file contents, not OS. CMake generates build/profile; the runner
checks the selected hash against the manifest and types against the ELF. An unknown
file stops configure before any server. Do not add a hash without reviewing signatures
and NULL guards. Provenance retains original migration hashes and extension notes.
The core API/schema is unchanged; this belongs to the fixture. CMake tracks the
profile, selector and RCC file to trigger reconfiguration.

## Validation and limits

Windows GCC13: 24/24 offline (22 prepare, traceability, inventory/imports/provenance).
Linux Docker: host PASS; HAL — 24 CTest, 22 prepare and five negative contracts PASS.
The selector is checked for both types and unknown-hash rejection.
Windows host also passed. Linux HW, GCC14/15 HAL and Release/LTO were not tested here.

The first HW suite passed 22 cases, 15 ADC/TIM3/RTC repeats after five injections,
expected timeout ERROR with an entry marker and reset_run host recovery, then ADC PASS.
Automatic restore stopped before the server due to WinError5 creating its report directory.
Original ERROR retained: tests/hal-f030/build/validation/20261001T154906.539459Z.
Separate restoration with permitted access: HW_BOOT/HW_BLINK PASS
(20261001T155154.356160Z and 20261001T155157.103743Z).
The final series after variant selection is recorded below.

Reproduce with build/prepare from the [fixture README](../../tests/hal-f030/README.en.md),
then run_hw.py with explicit --stand and --restore-session. NUCLEO-F030R8,
stock ST-Link/OpenOCD/SWD on Windows. Confirm the bench before running.
The suite stops on unexpected failure and attempts original firmware restoration.

These HAL cases do not increase the 98 historical CMSIS cases in README.
After CI and land, proceed to the F411 consumer; deleting old profiles remains a
separate step after its validation. H503/K1921 are unaffected.

## Final series

tests/hal-f030/build/validation/20261001T155503.591790Z/summary.json:
22/22 HW, 15/15 repeats, expected timeout ERROR/recovery, ADC after recovery PASS,
automatic restore HW_BOOT/HW_BLINK PASS; restored=true, MCU running.
ELF SHA256: `f2a2a2a98d8b95d080a78071543f7fd7d2a1f828dfaf3764c1ae53da39202fed`.
41 stages include one expected ERROR; this is not “41/41 PASS”.
Original failures remain recorded; no USB error occurred in this series.
