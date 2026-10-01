# HAL → CMSIS acceptance review for five profiles

[Documentation](index.md) · [Русский](../ru/CMSIS_ACCEPTANCE.md)

Snapshot on 2026-10-01: module `b8d66e0`, consumer
[stm32-hwtest-blackpill at 84a257e](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/tree/84a257e8825eeebaca3aed80e29cfe5f34235f53).
Reviewed `@case` declarations under consumer `profiles/*/tests/board`, shared
`tests/scenarios` implementations and module `tests/firmware/profiles/*/tests/board`.
Counts exclude experimental negative API cases, host tests, prepare and repeats.
This reviews source and recorded evidence; no new hardware run was performed.

## Inventory and evidence

| Profile | HAL board cases | CMSIS board cases | CMSIS hardware evidence |
| --- | ---: | ---: | --- |
| f030r8 | 17 | 18 | [F030 acceptance](F030_CMSIS_ACCEPTANCE.md): 16 + 1 + 1 on one ELF, not one 18/18 campaign |
| f103c8 | 22 | 20 | [F103 RTC/Sleep](F103_CMSIS_RTC_SLEEP.md), J-Link/SWD |
| f401cc | 22 | 20 | [F401 RTC/Sleep](F401_CMSIS_RTC_SLEEP.md), ST-Link/OpenOCD/SWD |
| f411ce | 22 | 20 | [F411 RTC/Sleep](F411_CMSIS_RTC_SLEEP.md), ST-Link/OpenOCD/SWD |
| f429zi | 22 | 20 | [F429 RTC/Sleep](F429_CMSIS_RTC_SLEEP.md), ST-Link/V2/OpenOCD/SWD |
| Total | 105 | 98 | Different revisions and ELFs; not one campaign on the current SHA |

Fewer CMSIS cases does not mean seven identical checks were lost: cases were
regrouped, HAL API checks replaced with register checks and new faults added.
Counts are not code coverage. Versions, ELF hashes and limits are recorded in
[metrics](HARDWARE_METRICS.md) and profile protocols. Windows HW does not establish
Linux HW support; GCC14/15 builds do not establish hardware results for those compilers.

## Group mapping

CMSIS IDs below omit `HW_CI_`; HAL IDs omit `HW_`.
F030 uses TIM3; the other profiles use TIM2.

| HAL | CMSIS | Preserved and changed evidence |
| --- | --- | --- |
| BOOT | BOOT | Startup, data and reaching the application; not exhaustive fault-path testing |
| CLOCK | CLOCK, ADC_INIT, TIMx_INIT | Clock configuration; CMSIS masks replace HAL predicates, not identical HAL PLL configuration |
| GPIO, BLINK | GPIO, BLINK | Profile pin/level, configuration and toggling; ticks do not prove physical period accuracy |
| TIMx_INIT, TIMx_IRQ | TIMx_INIT, TIMx_IRQ | Configuration and natural IRQ; no HAL handle/callback or intermediate pre-start state |
| ADC_DMA_INIT, ADC_DMA_RUNTIME | ADC_INIT, ADC_DMA | Scan/DMA, raw data and publication; IRQ replaces HAL callback/handle |
| ADC_UNITS, ADC_VECTORS, ADC_INVALID | ADC_UNITS, ADC_VECTORS, ADC_INVALID | Arithmetic, independent vectors and invalid inputs; profile calibration is not metrology |
| ADC_START_ERROR | ADC_BUSY | Changed evidence: busy ADC replaces forced HAL_ERROR; the HAL fixture retains the old path |
| ADC_DMA_TIMEOUT | ADC_TIMEOUT | Deadline without publication; IRQ disabling replaces HAL callback suppression |
| RTC_INIT, RTC_ALARM | RTC_INIT, RTC_ALARM | LSI/alarm/publication; F103 counter RTC differs from F0/F4 calendar RTC; no HAL callback checks |
| SLEEP_SYSTICK, SLEEP_TIMER | SLEEP_SYSTICK, SLEEP_TIMx | WFI, IRQ-source isolation and return; no HAL API, Stop/Standby or current measurement |
| No direct counterpart | RTC_DEADLINE | Wait-mask argument injection; neither physical LSI failure nor all wait states |
| No separate HAL case | SYSTICK_IRQ, ADC_DISABLED | Additional F103/F401/F411/F429 cases; no separate F030 cases |

The detailed F030 mapping remains in [its acceptance report](F030_CMSIS_ACCEPTANCE.md).
The [technique catalog](TESTING_TECHNIQUES.md) retains TECH-001…008: macro context,
IRQ/callback, injections, numerical vectors and interrupted WFI.

## What must remain available

The [F030 HAL fixture](F030_HAL_VALIDATION.md) has 17/17 hardware evidence and
preserves handles, callbacks, macros and ADC `force_return`. It does not cover all
F1/F4 HAL APIs. Four HAL profiles retain five additional cases:

| ID | Evidence not replaced by CMSIS or the F030 fixture |
| --- | --- |
| HW_GPIO_ARGUMENTS | GPIO_Init fields in HAL_GPIO_Init and applied configuration |
| HW_GPIO_FILTERED_CALL | Conditional stop at a selected HAL_GPIO_TogglePin call and ODR transition |
| HW_RCC_ERROR | force_return HAL_ERROR from HAL_RCC_OscConfig → Error_Handler |
| HW_RCC_OSC_NULL | RCC_OscInitStruct pointer changed to NULL → Error_Handler |
| HW_RCC_CLOCK_NULL | RCC_ClkInitStruct pointer changed to NULL → Error_Handler |

Before deleting sources, preserve these techniques as one group in the module's
standalone HAL regression: reuse the existing F030 fixture if its HAL supports
the intended checks; otherwise use a small F4 fixture. Review HAL source, DWARF
scope, function availability and source-review contracts before choosing. Moving
a technique to another family does not prove the other MCUs' HAL behavior.
Require build/prepare, hardware runs, positive repeats after injections,
recovery/restore and technique references. Keep the original profiles until then.

## Completion order

1. Accept RTC/Sleep `b8d66e0`, then its dependent documentation branch
   `codex/cmsis-migration-audit`. Both require Docs and full Offline.
2. Preserve the five additional HAL checks as one package. Select the bench
   after HAL review; no board reconnection is required for this review.
3. Migrate the independent BlackPill F411 consumer to CMSIS, update its gitlink
   after module acceptance; verify build/prepare, HW and recovery on F411CE/ST-Link.
4. Only then reduce the consumer to F411, retaining history and links to migrated
   examples, licenses, methods and protocols. H503 remains paused; do not delete
   K1921 and errata material as though STM32 fixtures replaced it.
5. Optimize CI after migration. An automated complete HW campaign and its metrics
   remain separate work; 98 historical cases do not replace that campaign.

The five-profile peripheral CMSIS baseline has hardware evidence; repository
separation is not complete. This review changes no core behavior, API, schemas
or specification requirements.
