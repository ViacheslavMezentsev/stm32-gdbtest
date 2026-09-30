# F030 CMSIS: TIM3 and IRQ

[Documentation](index.md) · [Русский](../ru/F030_CMSIS_TIMER.md)

Stage record: case counts and plans below refer to the stated revision.
Current scope: [STATUS](STATUS.md); release preparation: [rc.2](RC2_READINESS.md).

2026-09-30, `codex/f030-cmsis-timer` based on `40fafac`. NUCLEO-F030R8,
native ST-Link/SWD at 1 MHz, OpenOCD 0.12.0, Windows, GCC13.3.1-1.1,
GDB14.2.90/Python3.11.4. No UART or additional wiring.

## Implementation and evidence

TIM3 is an internal upcounter, PSC=7999, ARR=99 at APB=8 MHz (/1): nominal
100 ms period. UG loads PSC; its UIF is cleared before enabling IRQ.
NVIC IRQ16 is enabled; vector slot32 points to TIM3_IRQHandler. The handler
clears UIF by writing zero to that bit without read-modify-write and increments
the application periodic event counter board_timer_events.
Earlier external vector slots point to Default_Handler; later IRQ slots are
not yet present and must not be enabled before extending the vector table.
SysTick and LED retain the [baseline behaviour](F030_CMSIS_BASELINE.md).

- HW_CI_TIM3_INIT checks clock, PSC/ARR, SMCR, CR1, DIER, NVIC and vector.
- HW_CI_TIM3_IRQ observes three hardware handler entries with IPSR=32/UIF=1,
  two increments by exactly one, then progress back to thread mode. The final
  step detects an interrupt storm caused by a UIF that was never cleared.
- Previous BOOT/GPIO/CLOCK/BLINK scenarios repeated: **6/6 HW PASS**.

ELF SHA256: `4d410c04ae6aee1fa6347cc95cc68d3b2c7579281f3b01899a2056397d5c0342`.
Final JSON/JUnit: tests/firmware/build/f030r8/hwtest/runs/, series
20260930T131107…20260930T131117; logs build/f030-cmsis-timer/*-final.log.
The consumer HAL firmware was restored afterwards: HW_BOOT PASS,
20260930T131120, teardown reset_run. MCU left running.

## Mapping and limitations

HW_TIM3_INIT → HW_CI_TIM3_INIT preserves PSC/ARR and the internal clock;
it observes an already running timer rather than the state before HAL setup.
HW_TIM3_IRQ → HW_CI_TIM3_IRQ preserves periodic handler effects and adds
IPSR/vector/thread progress; HAL handles and callbacks are not covered.
Tests do not write EGR or NVIC pending bits. GDB halts may coalesce UIF events;
entry counts do not prove absence of lost events or an accurate period.
The event counter is application state, not a test hook. TIM3 can now also
wake WFI; this is not yet a separate Sleep test.

Repeat: build preset f030r8, CTest f030r8-offline, then the regular CLI:
`python -B -m stm32_gdbtest run --session tests/firmware/build/f030r8/hwtest/session.json --test <ID> --stand <local.toml>`.
run_hw.py retains its original ten BOOT/GPIO steps; new scenarios use the CLI.
ADC/DMA/RTC and HAL-specific fixtures remain planned.

Local offline regression: F030 CTest 7/7; Windows host 96 (8 skips); Linux Docker docs/host and F030/F103/F411 × GCC13/14/15 — 13/13 PASS. Git index archive extracted on a case-sensitive filesystem. Modified C source formatting and strict specification checks: PASS.
