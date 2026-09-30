# F030 CMSIS: Sleep/WFI and interrupt sources

[Documentation](index.md) · [Русский](../ru/F030_CMSIS_SLEEP.md)

Stage record: case counts and plans below refer to the stated revision.
Current scope: [STATUS](STATUS.md); release preparation: [rc.2](RC2_READINESS.md).

2026-09-30, codex/f030-cmsis-sleep based on a84b742. NUCLEO-F030R8,
native ST-Link V2J45M31/SWD 1 MHz, OpenOCD0.12.0, Windows,
GCC13.3.1-1.1/GDB14.2.90/Python3.11.4; no UART/additional wiring.
Firmware and core unchanged; new scenarios and CI prepare only.

## Method

Scenarios enter board_delay_ms with delay_ms=500 after ADC publication.
SCR SLEEPDEEP/SLEEPONEXIT must be clear. Logged NVIC/SysTick mutations
isolate SysTick or TIM3. The TIM3 case stops SysTick and clears pending
SysTick through ICSR.PENDSTCLR.

At the handler, check IPSR (15/32), then unwind the interrupted frame using
GDB Frame.older/type/pc/name, skipping signal trampolines. Require
board_delay_ms and halfword 0xBF30 (WFI) immediately before the interrupted PC.
An IRQ can arrive before WFI; allow at most eight attempts and record every
context. No WFI context is FAIL; inability to unwind is ERROR, with no weaker
fallback PASS. This is a profile-specific Cortex-M test, not a generic core
facility for other architectures.

Controls are restored in finally; normal teardown also performs reset_run.
After restoration, reach app_loop, check counter progress and retained ADC
sequence 1. With SysTick disabled its counter must remain unchanged in the
TIM3 case. Reading SysTick CTRL clears COUNTFLAG, unused by the application.

## Evidence

**2/2 new HW PASS**, 20260930T163701/20260930T163704. SysTick first attempt:
interrupted PC=0x080001BC, preceding instruction WFI. TIM3 first stop is
before WFI (PC=0x080001B4, halfword 0x2000); second is after WFI
(PC=0x080001BC). A handler breakpoint alone would provide weaker evidence.
ELF SHA256 matches the ADC units stage:
`cd52b5cbac535952fb4069b067c9e24bf536172126c0a98bdd40548a89e3e01b`.
The previous 12 scenarios were not rerun here; this is not a single 14/14
series. [Previous evidence](F030_CMSIS_ADC_UNITS.md) applies to the same ELF.
JSON/JUnit: tests/firmware/build/f030r8/hwtest/runs/;
logs: build/f030-cmsis-sleep/. HAL restored, HW_BOOT PASS
20260930T163707, reset_run; MCU left running.

## Limits

Preserves HW_SLEEP_SYSTICK/TIMER intent: ordinary Sleep path and subsequent
progress, adding interrupted-PC analysis. No DHCSR.S_SLEEP observation,
residency/current/wake-latency measurement. WFI could complete quickly due to
a pending IRQ; debugging affects execution. This is not Stop/Standby.
GCC14/15 are build/prepare checks; their unwind behaviour remains untested
on hardware. HAL_PWR_EnterSLEEPMode is not called or covered. Next: RTC and
explicit acceptance of remaining HAL-specific/failure coverage before migration ends.

Local: F030 CTest 15/15; Windows host 96 (8 skips); Linux Docker docs/host and F030/F103/F411 × GCC13/14/15 — 13/13 stages PASS. Git index archive extracted on a case-sensitive filesystem; strict specification check PASS.
