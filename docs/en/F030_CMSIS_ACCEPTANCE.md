# F030: HAL → CMSIS acceptance mapping

[Documentation](index.md) · [Русский](../ru/F030_CMSIS_ACCEPTANCE.md)

Third batch branch: codex/f030-cmsis-acceptance based on codex/f030-rtc-deadline
(`769226b`). Reviewed the consumer's17 F030 HAL cases at `50adc35` and18 CMSIS
cases in tests/firmware. Case counts are not code coverage.

## Evidence mapping

| HAL case | CMSIS case (HW_CI_ prefix) | Preserved / changed / not migrated |
| --- | --- | --- |
| HW_BOOT | BOOT | main/app_loop, BSS/initialized data; fault trap retained, no separate HardFault injection |
| HW_CLOCK | CLOCK, ADC_INIT, TIM3_INIT | HSI8/AHB/APB /1 and ADC/DMA/TIM3 clocks; split across cases, no HAL RCC predicates |
| HW_GPIO | GPIO | PA5 mode/type/speed/pull/initial Low preserved |
| HW_BLINK | BLINK | High/Low and ≥500 SysTick ticks; no physical period accuracy claim |
| HW_ADC_DMA_INIT | ADC_INIT | ADC/DMA registers, scan16/17, sampling, normal halfwords; no HAL handle fields |
| HW_ADC_DMA_RUNTIME | ADC_DMA | Two completions, raw data/publication; DMA IRQ replaces HAL callback, handle check lost |
| HW_TIM3_INIT | TIM3_INIT | PSC7999/ARR99; CMSIS checks a running timer, intermediate HAL CEN=0 not migrated |
| HW_TIM3_IRQ | TIM3_IRQ | Natural IRQ/UIF/counter/thread mode; no HAL callback handle |
| HW_RTC_INIT | RTC_INIT | LSI,127/311, enable/output off; adds EXTI/NVIC/vector/masks |
| HW_RTC_ALARM | RTC_ALARM | Two natural Alarm A events/publication; no HAL callback/handle |
| HW_ADC_START_ERROR | ADC_BUSY | Replacement: actual busy ADC → error6; HAL_ERROR force_return and HAL path not migrated |
| HW_ADC_DMA_TIMEOUT | ADC_TIMEOUT | Missing publication → deadline; DMA IRQ disabled instead of suppressing HAL callback |
| HW_ADC_UNITS | ADC_UNITS | F030 calibration, quality3/sanity; not sensor accuracy |
| HW_ADC_INVALID | ADC_INVALID | Invalid inputs → zeros, then recovery; expanded to four inputs and boundaries |
| HW_ADC_VECTORS | ADC_VECTORS | Analytic anchor plus vectors; fixed expectations and C integer truncation |
| HW_SLEEP_SYSTICK | SLEEP_SYSTICK | Ordinary Sleep IRQ/progress, adds interrupted WFI context; no HAL call check |
| HW_SLEEP_TIMER | SLEEP_TIM3 | TIM3 isolation from SysTick, WFI context/progress; not current measurement |

RTC_DEADLINE additionally checks the shared wait with mask=0 injection,
not physical LSI failure or every RTC error path.

## Evidence

One ELF SHA256 `b911213338acc2de1b0d47a41d7c0b23a50974ba8f78370e041f2afbc2a00e9e`:
16/16 at the [RTC stage](F030_CMSIS_RTC.md), then separate [ADC_BUSY](F030_ADC_BUSY.md)
and [RTC_DEADLINE](F030_RTC_DEADLINE.md) runs; not one complete18/18 run.
Normal ADC_DMA and RTC_ALARM passed again after injections.
NUCLEO-F030R8/ST-Link/SWD/OpenOCD, Windows/GCC13; HAL restored/running.
GCC14/15: build/prepare only. Other backends/OS hardware paths not tested in this batch.

## Decision and remaining work

F030 functional CMSIS baseline is established within these limits. Do not remove
the consumer's HAL profile yet: it retains HAL contracts/macros, callback handle
and force_return regression. A separate minimal HAL fixture in the module must
preserve those checks before removal; old results cannot replace a new run.

ADC DMA TE/clock/calibration/ready faults and RTC source mismatch/other stages
remain open. Backup retention, rollover, accuracy, Stop/Standby and consumption
are separate tasks, not acceptance criteria for this baseline. CMSIS F103/F411
preparation can proceed without deleting F030 HAL or claiming migration of all
profiles. Agree a stand change with the owner separately.

## Branch batch

1. codex/f030-adc-busy, `3ba9c26`, base `5d09823`.
2. codex/f030-rtc-deadline, `769226b`, based on branch1.
3. codex/f030-cmsis-acceptance, based on branch2; documentation only.

The owner pushes all three branches. Docs and all Offline jobs must complete
for each SHA. Land sequentially with fast-forward, without squash or changing
verified commits. Any rebase requires CI for the new SHA. Push does not authorize
land. Once the batch is accepted, update the consumer gitlink once in its own
branch with consumer CI.

## Local batch checks

Each of the three snapshots separately passed Linux Docker docs/host and nine
firmware pairs F030/F103/F411 × GCC13/14/15:13/13 stages per branch.
Reports: build/f030-fault-batch/b1, b2, b3/linux-ci/summary.json.
Windows host:96 tests,8 skips; F030 CTest:18/18 on branch1,19/19 on branch2
(branch3 changes documentation only). Original RTC ERROR:
20260930T173151.880173Z-HW_CI_RTC_DEADLINE-35952; fixed PASS and restoration are
recorded in the protocol. GitHub CI still needs checking for each published SHA.

Publication update: the batch, including the fourth naming branch, is in
main `cea01f9`; Docs and all five Offline jobs succeeded for each SHA. The
consumer update landed at `0c8c966` after five-profile CI. Next step:
[separate HAL regression](F030_HAL_REGRESSION.md).
