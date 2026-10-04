# CI firmware

Minimal CMSIS-only firmware used by CI to check stm32-gdbtest up to the GDB server:
build, build manifest, collection, traceability, offline ELF contracts and
`run --prepare-only`. Profiles `f030r8` (Cortex-M0), `f103c8` (Cortex-M3),
`f401cc`, `f411ce` and `f429zi` (Cortex-M4) mirror boards validated in stm32-hwtest-blackpill. The
scenarios check register state and are not evidence of HAL behaviour.

Toolchain: `ARM_TOOLCHAIN_ROOT`; CMSIS: `STM32CUBE_REPOSITORY` with
`STM32Cube_FW_F0_V1.11.6`, `STM32Cube_FW_F1_V1.8.7`, `STM32Cube_FW_F4_V1.28.3`.
Usually run through `ci/run_checks.py` inside the CI Docker image. On a local
Windows or Linux stand `run_hw.py` runs the boot/GPIO scenarios on hardware (see
docs/en/testing.md and docs/en/LINUX_STAND.md).
LEDs: NUCLEO-F030R8 PA5, WeAct BluePill-Plus PB2, WeAct BlackPill F401/F411 PC13, STM32F429I-DISCO PG13.
C sources follow the repository `.clang-format`.

F030 also provides CLOCK/BLINK scenarios through the regular CLI. Its LED interval
is 500 SysTick milliseconds; see [baseline evidence](../../docs/en/F030_CMSIS_BASELINE.md).

F030 RTC owns and resets the calendar on boot, but never resets the backup domain.
See [RTC evidence and limitations](../../docs/en/F030_CMSIS_RTC.md).

## Current example scope

F030 has 18 scenarios covering boot/clock/GPIO/blink, TIM3, ADC/DMA and numeric
vectors, RTC, Sleep and selected failure paths. F103 now has 20 cases including ADC/DMA, typical units, RTC, Sleep and failure paths; F411 has twenty baseline/ADC/DMA/factory-unit/RTC/Sleep/failure
scenarios. This is not peripheral parity across profiles.
The separate [HAL F030 fixture](../hal-f030/README.en.md) preserves HAL-specific
contracts, handles/callbacks and force_return checks.

`run_hw.py` exercises the runner lifecycle using boot/GPIO, not all F030 cases.
Use the explicit hardware suite described in the [rc.2 plan](../../docs/en/RC2_READINESS.md)
for candidate acceptance. The [status](../../docs/en/STATUS.md) distinguishes
historical results from checks of the current candidate.

Two application scenarios exist on every profile and check the scenario API itself:
`HW_CI_RET_RECEIVER` (a forced return from `app_step` reaches the calling
`app_receiver_step`, which stores it in `app_received`) and `HW_CI_MEASUREMENT_SERIES`
(five ADC publications with execution continuing between samples, real spread and an
advancing publication counter). They use only the public scenario API and are meant to
be repeated after a package transfer; `src/app_receiver.c` is an ordinary application
module, not a test hook.

F103 RTC uses a counter/alarm and thread-mode rearming, unlike the F030 calendar.
See [RTC/Sleep evidence and limits](../../docs/en/F103_CMSIS_RTC_SLEEP.md).

[F411 ADC/DMA evidence](../../docs/en/F411_CMSIS_ADC_DMA.md) covers stream DMA and factory calibration.

[F411 RTC/Sleep evidence](../../docs/en/F411_CMSIS_RTC_SLEEP.md) covers calendar alarms, WFI and recovery.

[F401 baseline evidence](../../docs/en/F401_CMSIS_BASELINE.md): seven clocks/GPIO/TIM2/SysTick cases. F401 uses the regular CLI, not the three-profile run_hw.py helper.

[F401 ADC/DMA evidence](../../docs/en/F401_CMSIS_ADC_DMA.md):15 cases, CH16/17 and shared adc_convert_f4_factory arithmetic.

[F401 RTC/Sleep evidence](../../docs/en/F401_CMSIS_RTC_SLEEP.md):20 cases, deadline and host recovery; rtc_f4.c and vectors are shared with F411.

[F429 baseline](../../docs/en/F429_CMSIS_BASELINE.md): seven startup/clocks/GPIO/TIM2/SysTick cases, HSI16 MHz, SRAM192 KiB without CCM. RTC covered by the subsequent group below.

[F429 ADC/DMA](../../docs/en/F429_CMSIS_ADC_DMA.md):15 cases, SRAM bounds, factory units and state faults.

[F429 RTC/Sleep](../../docs/en/F429_CMSIS_RTC_SLEEP.md):20 cases, deadlines and host recovery; RTC code/vectors shared with F401/F411.
