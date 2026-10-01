# F401 CMSIS: clocks, GPIO, SysTick and TIM2

[Documentation](index.md) · [Русский](../ru/F401_CMSIS_BASELINE.md)

2026-10-01, working tree `codex/f401-cmsis-baseline` based on main `591c096`.
WeAct BlackPill v3.0 marked STM32F401CCU6, ST-Link/SWD, OpenOCD0.12.0,
Windows/GCC13.3.1-1.1/GDB14.2.90. The owner replaced the board; no UART required.

## Profile and implementation

Flash256 KiB, RAM64 KiB; expected DEV_ID0x423. This experiment read exactly
0x423 and 256 KiB: identity.matches=true, no warnings. This does not reassess
historical specimens with other device IDs. Existing warn/strict policy remains;
the detected ID does not expand profile memory limits.

CMSIS STM32F401xC comes from CubeF4 V1.28.3. GPIO/RCC/TIM2/SysTick share the
F411 board.c branch; F401 startup has its own vectors through IRQ28. Checked
CMSIS stm32f401xc.h and the consumer's existing F401 profile. F411 ADC/RTC
functions are not linked into F401, including the ADC call in app_loop.
Their channels, calibration and IRQs will be handled separately.

HSI16 MHz, AHB/APB1/APB2 /1; PC13 low-speed push-pull, initially High,
active-low LED. SysTick reload15999, LED interval500 firmware ticks. TIM2 uses
internal clock, PSC15999/ARR99: nominal100 ms. UG loads the prescaler and UIF
is cleared before NVIC enable; the ISR clears UIF by writing zero and publishes events.

## Checks and mapping

| Cases | Evidence |
| --- | --- |
| BOOT, GPIO, CLOCK, BLINK | .data/BSS, app_loop entry, GPIO/RCC/SysTick registers, alternating PC13 |
| TIM2_INIT, TIM2_IRQ | PSC/ARR/NVIC/vector44, two natural IRQs and thread-mode return |
| SYSTICK_IRQ | vector15/exception15, tick counter and thread-mode return |

Cases derive from the accepted [F411 baseline](F411_CMSIS_BASELINE.md), using
CMSIS macros in board.c and [TECH-001/002](TESTING_TECHNIQUES.md). Frequency,
pin and IRQ expectations are recorded in requirements.md; these are not HAL calls.
Original HAL boot/clock/GPIO/blink/TIM2 checks retain final-state and IRQ evidence;
HAL arguments, handles/callbacks and force_return are not covered.

Windows build and prepare/traceability **8/8 PASS**; HW **7/7 PASS** through the
standard CLI, with image_verified and reset_run in all reports. Original F401
HAL firmware was then restored; HW_BOOT/HW_BLINK PASS, MCU left running.
ELF SHA256: `c6a5cb4f319ed0b0ff2640ec2578d5cc0df3af2f424807fe21d0b4ce4fbad784`.
Artifacts: build/f401-cmsis-baseline/f401-windows-full-20261001T130710Z/summary.json
and tested-source-hashes.json nearby. The base SHA does not identify modified sources.
The first local harness attempt stopped before connecting due to an f401ce
session-path typo; the recorded series ran after correcting it.

Presets `f401cc`, `f401cc-offline` are in tests/firmware. Offline CI adds F401
to the previous three MCUs on GCC13/14/15. Hardware workflow/run_hw.py retain
their previous three-board list; baseline uses regular CLI run with a profile
session and explicit ST-Link stand. Automated F401 HW matrix, full-image,
timeout/recovery and other backends were not tested in this stage. No claim
of HSI accuracy, jitter/loss-free IRQs or isolated WFI wakeup is made.
Next groups: ADC/DMA/units/failures, then RTC/Sleep/recovery.

Local regression: Windows docs/host4/4 (98 unittest, 8 platform skips); network-free Linux Docker format/host and 12 MCU/GCC combinations — 14/14 PASS. Reports: build/f401-cmsis-baseline/linux-source/build/ci/summary.json. GitHub Docs/full Offline are checked after pushing the new SHA, before land.
