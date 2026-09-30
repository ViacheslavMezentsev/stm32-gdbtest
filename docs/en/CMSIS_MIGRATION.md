# Migrating minimal examples to CMSIS

[Documentation](index.md) → Example migration · [Русский](../ru/CMSIS_MIGRATION.md)

Owner decision, 2026-09-30: minimal examples and the current regression matrix
belong in stm32-gdbtest. After CMSIS migration, the BlackPill repository keeps
an independent F411 consumer in maintenance mode, following BluePill.
Firmware and application-specific scenarios remain outside the module core.

At `bc07625`, CMSIS-only `tests/firmware` already covers F030/F103/F411;
`examples/minimal-consumer` targets F411. Reuse these without duplication:
the first is a regression fixture, the second demonstrates integration.
F401/F429 remain to be added; H503 stays paused. CMSIS applies to ARM;
RISC-V needs its own startup/BSP.

## F030: comparison with 17 HAL scenarios

First stage complete: [boot/clock/GPIO/blink](F030_CMSIS_BASELINE.md) — 4/4
on Nucleo/ST-Link/OpenOCD. The table below retains the original inventory;
the peripheral portion of HW_CLOCK is still pending.

Source: BlackPill f030r8 profile at `7a198d1`. The two existing CMSIS scenarios
do not replace all 17 original checks.

| Original scenarios | CMSIS fixture / missing evidence |
| :--- | :--- |
| HW_BOOT | HW_CI_BOOT checks app_loop/ticks; retain separate main/fault checks |
| HW_GPIO | HW_CI_GPIO checks PA5 clock/output; add push-pull, pull, speed, initial level |
| HW_CLOCK | Add independent frequency/divider and peripheral clock expectations |
| HW_BLINK | Add High/Low and ≥500 ms interval; app_state.ticks is not milliseconds |
| HW_ADC_DMA_INIT, HW_ADC_DMA_RUNTIME | No ADC/DMA; add configuration, completion, publication |
| HW_TIM3_INIT, HW_TIM3_IRQ | No TIM3/IRQ; add configuration and handler effects |
| HW_RTC_INIT, HW_RTC_ALARM | No RTC; add configuration and recurring event |
| HW_ADC_START_ERROR, HW_ADC_DMA_TIMEOUT | Define CMSIS driver failure/deadline; retain HAL injection in a separate fixture |
| HW_ADC_UNITS, HW_ADC_INVALID, HW_ADC_VECTORS | Migrate arithmetic, calibration and independent numeric expectations |
| HW_SLEEP_SYSTICK, HW_SLEEP_TIMER | Migrate WFI/wake sources and debugger-impact limitations |

Local check, 2026-09-30: Windows, GCC13.3.1-1.1, f030r8 preset — build PASS,
`ctest --preset f030r8-offline` 3/3 (two prepare tests and traceability).
The runner did not connect to hardware or change its firmware. No new HW PASS.

## Acceptance sequence

1. Complete F030 boot/clock/GPIO/blink, then validate on Nucleo with native
   ST-Link/SWD; state the backend and HAL firmware restoration procedure before HW.
2. Migrate timer/IRQ, ADC/DMA/arithmetic, RTC, Sleep and failures separately.
   Record preserved, changed or lost evidence for each scenario.
3. Review F103/F411 and add F401/F429. Retain separate regression for HAL-specific
   APIs/macros: CMSIS firmware does not test them.
4. Publish and accept examples here before removing active BlackPill copies.
   Preserve historical reports; maintain the new matrix here with SHA, ELF,
   MCU/backend/toolchain and limitations. Old PASS does not carry over.
5. Optimize CI after migration: measure stages, eliminate repeated host suites,
   consider caching while preserving the evidence set.

No API/schema/version changes yet. This plan does not confirm new MCU support
or resume the K1921 stand. The F411 application remains an independent consumer;
the module's small F411 fixture exercises infrastructure.

TIM3/IRQ stage completed: [6/6 HW PASS, mapping and limitations](F030_CMSIS_TIMER.md).

F030 ADC/DMA: raw samples and timeout, core API unchanged. [ADC/DMA](F030_CMSIS_ADC_DMA.md).

F030 ADC conversion and numeric scenarios; core API unchanged. [ADC units](F030_CMSIS_ADC_UNITS.md).

F030 Sleep/WFI: profile scenarios using GDB unwind; core API unchanged. [Sleep evidence](F030_CMSIS_SLEEP.md).

F030 RTC: LSI Alarm A, 16/16 HW PASS, HAL restored. Core API unchanged. [RTC](F030_CMSIS_RTC.md).

F030 busy ADC check; API unchanged. [Report](F030_ADC_BUSY.md).
