# F429 CMSIS: startup, clocks, GPIO, TIM2 and SysTick

[Documentation](index.md) · [Русский](../ru/F429_CMSIS_BASELINE.md)

2026-10-01, working tree codex/f429-cmsis-baseline based on main `9d22410`.
STM32F429I-DISCO (older board), STM32F429ZIT6, built-in ST-Link/V2,
CN1/SWD, OpenOCD0.12.0, Windows, GCC13.3.1-1.1/GDB14.2.90.
Owner confirmed wiring; no UART or additional wiring is needed.

## Profile and configuration

STM32F429xx CMSIS from CubeF4 V1.28.3. Flash 2 MiB, ordinary SRAM 192 KiB;
CCM 64 KiB is excluded from the linker. Future DMA groups must use SRAM.
Expected DEV_ID 0x419; this series read 0x419 and 2048 KiB, identity.matches=true.
Sources were checked against the consumer's existing F429 HAL profile,
linker, GPIO configuration and CMSIS stm32f429xx.h.

The minimal example uses HSI 16 MHz, AHB/APB1/APB2 /1, without PLL.
This deliberately changes the previous HAL configuration
(PLL 64 MHz, AHB/8, HCLK 8 MHz); it does not validate that PLL configuration.
LD3/PG13 is active-high, push-pull low-speed with no pull, initially Low.
SysTick LOAD 15999 gives a nominal 1 ms tick; LED toggles every 500 ticks.
TIM2 PSC=15999/ARR=99: nominal 100 ms, IRQ28/vector44.
Startup copies .data and clears BSS; pending/UIF is cleared before enabling IRQ.

board.c and startup.c have separate F429 branches; ADC/RTC are neither called
nor included in this build. Core API, schemas and version 0.1.0rc2 are unchanged.

## Checks and limits

| HW_CI_* | Evidence |
| --- | --- |
| BOOT | .data/BSS at main, app_loop reached and counter advances |
| GPIO, BLINK | PG13 registers, initially Low, alternating after ≥500 firmware ticks |
| CLOCK | HSI/SYSCLK, dividers, SystemCoreClock and SysTick |
| TIM2_INIT, TIM2_IRQ | PSC/ARR/NVIC/vector44, natural IRQs, publication and thread resumption |
| SYSTICK_IRQ | vector15/exception15, tick counter, thread resumption |

[TECH-001/002/003](TESTING_TECHNIQUES.md): CMSIS macros in board.c context,
natural IRQs and independent expectations. Previous HAL boot/GPIO/timer evidence
is retained at the final-state/handler level, without handles/callbacks, HAL arguments
or force_return. Register checks do not prove emitted LED light.
HSI accuracy, jitter, missed IRQs and isolated WFI were not measured.

## Results and reproduction

Windows build, prepare/traceability **8/8 PASS**. Hardware **7/7 PASS**,
image_verified and reset_run in every report. The original HAL firmware was
restored afterwards, HW_BOOT/HW_BLINK PASS; MCU was left running.
ELF SHA256: `237d2926b19f8c745c4745b7a1ef2a5fe0e60d58ab6316d23d1c0b8676ac8024`.
Artifacts under build/f429-cmsis-baseline: f429-windows-full-20261001T140318Z/summary.json
and tested-source-hashes.json. The base SHA does not identify modified code.
Personal paths/serial, ELF and JSON/JUnit are not committed.

Use f429zi/f429zi-offline presets in tests/firmware. From module root:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f429zi/hwtest/session.json --test <ID> --stand <local.toml>`.
Select the DISCO/OpenOCD stand explicitly; restore original HAL and check boot/blink in finally.
The run_hw.py hardware helper retains its three-board matrix; the seven new
cases use the regular CLI. CI build/prepare adds the fifth profile on GCC13/14/15.

This short series had no USB errors; it does not invalidate the historical
ST-Link/V2 limitation during repeated launches. Stop at the first failure;
USB reconnection requires coordination with the owner. Debugger firmware was unchanged.
ADC/DMA/units/failures and RTC/Sleep/deadline/recovery are the next groups.
New backends, Linux HW, timeout/recovery and full-image HW were not checked here.
Published-SHA GitHub Docs/full Offline are checked separately before land.

Local regression: Windows docs/host4/4 (98 unittests, 8 platform skips); Linux Docker format/host and 15 MCU/GCC combinations — 17/17 PASS. Logs: build/f429-cmsis-baseline/linux-source/build/ci; Windows: windows-docs-host.json and windows-host.log alongside. Historical CMSIS snapshot updated to 5 board models / 85 cases; repeats are excluded.
