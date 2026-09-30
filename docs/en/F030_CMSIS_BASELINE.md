# F030: baseline CMSIS checks

[Documentation](index.md) → F030 CMSIS · [Русский](../ru/F030_CMSIS_BASELINE.md)

Stage record: case counts and plans below refer to the stated revision.
Current scope: [STATUS](STATUS.md); release preparation: [rc.2](RC2_READINESS.md).

2026-09-30, branch `codex/f030-cmsis-baseline` based on `4601888`.
NUCLEO-F030R8, native ST-Link/SWD at 1 MHz, OpenOCD; Windows runner,
xPack GCC13.3.1-1.1, GDB14.2.90/Python3.11.4. No UART connection.
CMSIS-only fixture: `tests/firmware`, no HAL or test hooks.

## Changes

F030 only: HSI 8 MHz, AHB/APB /1, PA5 push-pull/low speed/no pull,
initially Low. SysTick LOAD=7999 drives the millisecond counter;
app_delay=500 sets the LED toggle interval. The wait uses WFI.
app_state.ticks still counts iterations, not milliseconds.
F103/F411 retain their previous behavior.

The constant reload is calculated at compile time: dividing mutable
SystemCoreClock on Cortex-M0 would require libgcc __aeabi_uidiv with the
current -nostdlib build. This profile has a fixed clock; dynamic clock
switching is outside its scope.

## Hardware result

| Scenario | Evidence | Result |
| :--- | :--- | :--- |
| HW_CI_BOOT | main, .data/.bss values, app_loop, advancing counter | PASS |
| HW_CI_GPIO | PA5 clock/output, push-pull, speed, pull, initial Low | PASS |
| HW_CI_CLOCK | HSI ready/selected, dividers, SystemCoreClock, SysTick LOAD/CTRL | PASS |
| HW_CI_BLINK | Low → High → Low; ≥500 firmware ms between stops | PASS |

ELF SHA256: `05e6e50802131edb3cbfa1dd8e71db5830422a0bb35439031b732701b69668ea`.
All four reports: `teardown=reset_run`. Local logs:
`build/f030-cmsis-baseline/`; JSON/JUnit: `tests/firmware/build/f030r8/hwtest/runs/`.
The previous BlackPill-project HAL firmware was restored afterwards:
HW_BOOT PASS, reset_run. The stand is running the HAL application.

Repeat: configure/build the f030r8 preset, run CTest f030r8-offline, then use
`python -B -m stm32_gdbtest run --session tests/firmware/build/f030r8/hwtest/session.json
--test <ID> --stand <local.toml>` for each of the four IDs with an explicit stand.
The original ten run_hw.py steps do not include CLOCK/BLINK; this experiment
does not claim a full rerun of those steps or validation of other backends.

## Limits

Debugger stops affect timing. No HSI accuracy, current consumption, optical
blink or external frequency measurement. Reading SysTick CTRL clears COUNTFLAG;
the application uses the IRQ counter instead. Using WFI does not by itself
validate the previous HW_SLEEP_* scenarios.
ADC/DMA/TIM3/RTC and HAL-specific failures remain in the migration plan.

Offline regression: Windows host 96 tests (8 skips); Linux Docker, Git index archive extracted on a case-sensitive filesystem — docs/host and nine F030/F103/F411 × GCC13/14/15 pairs: 13/13 PASS. Modified C source formatting and strict specification checks passed.
