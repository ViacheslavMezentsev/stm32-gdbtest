# Migrating minimal examples to CMSIS

[Documentation](index.md) → Example migration · [Русский](../ru/CMSIS_MIGRATION.md)

Owner decision, 2026-09-30: minimal examples and the current regression matrix
belong in stm32-gdbtest. After CMSIS migration, the BlackPill repository keeps
an independent F411 consumer in maintenance mode, following BluePill.
Firmware and application-specific scenarios remain outside the module core.

At `bc07625`, CMSIS-only `tests/firmware` already covers F030/F103/F411;
`examples/minimal-consumer` targets F411. Reuse these without duplication:
the first is a regression fixture, the second demonstrates integration.
F401 is migrated; F429 is being migrated in groups; H503 stays paused. CMSIS applies to ARM;
RISC-V needs its own startup/BSP.

## F030: current mapping

The [17 HAL →18 CMSIS acceptance table](F030_CMSIS_ACCEPTANCE.md) replaces the
initial inventory. Basic functions passed on Nucleo/ST-Link; HAL-specific
handles/macros/force_return are preserved in the separate
[HAL F030 fixture with hardware acceptance](F030_HAL_VALIDATION.md). Migration of all
MCUs is incomplete; retain the active HAL profile for now.

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

F030 RTC deadline through argument injection; API unchanged. [Report](F030_RTC_DEADLINE.md).

## Next work groups

After rc.2: one branch per 3–4 related capabilities, several local commits,
one push after combined validation, then full CI and land. Groups: clocks/GPIO/
timer/IRQ; ADC/DMA/arithmetic/failures; RTC/Sleep/deadlines/recovery. F103 first,
then F411; update the consumer gitlink after multiple groups as needed.
First F103 group: [7/7 HW and HAL restoration](F103_CMSIS_BASELINE.md).

F103 ADC/DMA: [15/15 HW, units and failure paths](F103_CMSIS_ADC_DMA.md).

[F401 baseline](F401_CMSIS_BASELINE.md): 7/7 HW in the first group; ADC/DMA and RTC/Sleep completed in subsequent groups.

[F401 ADC/DMA](F401_CMSIS_ADC_DMA.md):15/15 HW and post-injection repeats; continued by [RTC/Sleep/recovery,20/20 HW](F401_CMSIS_RTC_SLEEP.md).

[F429 CMSIS baseline:7/7 HW, HAL restored; specification0.55. Fifth CI profile; ADC/RTC remain pending.](F429_CMSIS_BASELINE.md)

[F429 ADC/DMA/units/failures:15/15 HW +3 repeats, HAL restored; specification0.56.](F429_CMSIS_ADC_DMA.md)
