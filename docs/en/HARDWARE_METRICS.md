# Hardware validation metrics

[Documentation](index.md) · [Русский](../ru/HARDWARE_METRICS.md)

Snapshot dated 2026-10-01, with sources available in main `91a7cd4`. README
badges are currently static and updated with this table after reviewing evidence.
The blue `Hardware: historical snapshot` describes the evidence category, not
the health of current CI. Docs and Offline retain their independent statuses.

## Included results

Only the `tests/firmware` CMSIS fixtures for these three board models are counted.
This is a bounded historical set, not every board or execution in project history.

| Board model / MCU | Debugger and backend | Cases with evidence | Report and accepted stage revision |
| --- | --- | ---: | --- |
| NUCLEO-F030R8 / STM32F030R8T6 | Onboard ST-Link, OpenOCD/SWD | 18 | [HAL → CMSIS](F030_CMSIS_ACCEPTANCE.md), batch accepted at `cea01f9`; 16 + 1 + 1 on one ELF, not one 18/18 series |
| WeAct BluePill-Plus / STM32F103C8T6 | J-Link, SWD | 20 | [RTC/Sleep and preceding groups](F103_CMSIS_RTC_SLEEP.md), `d97903c`, 2026-10-01 |
| WeAct BlackPill V3.1 / STM32F411CEU6 | ST-Link, OpenOCD/SWD | 20 | [RTC/Sleep and preceding groups](F411_CMSIS_RTC_SLEEP.md), `91a7cd4`, 2026-10-01 |
| **Total** | **3 board models** | **58** | **Historical snapshot across revisions** |

All rows refer to Windows, xPack GCC13.3.1-1.1/GDB14.2.90. Reports provide
exact ELF hashes, local artifacts, original errors and experiment boundaries.
An accepted stage revision locates the history; it does not claim every run
used a clean checkout of that commit. F030 includes separate scenario fixes;
the original RTC error remains in the history after the successful repeat.

## Badge definitions

- `Boards tested: 3` counts distinct board models with a specific MCU in the table.
  Two physical specimens of one model or two backends do not increase it.
  A debugger identifier is not a board identifier.
- `HW cases (recorded): 58` sums distinct profile/fixture/scenario-ID combinations
  with confirmed results in these reports. It is not 58 different test algorithms,
  an assertion count or a coverage percentage.
- `HW verified (latest): 2026-10-01` is the newest included experiment date,
  not the verification date of all rows or current main.
- `Hardware: historical snapshot` means there is no single complete campaign
  at one SHA from which to derive a current aggregate PASS/FAIL.

Post-injection repeats, original HAL restoration, the 17 `tests/hal-f030` cases,
consumer checks, builds/prepare and old PoCs are excluded from this total.
They retain their own results. An expected failure counts as a successful
contract check only when verified by its outer scenario; an inner ERROR
alone is not a successful test.

## Updating and next stage

When updating the snapshot, review evidence and the table total, then update
both README languages, this page and CHANGELOG together. Static badges do
not change automatically when a GitHub workflow is rerun. The current
[Hardware workflow](../../.github/workflows/hardware.yml) uses `run_hw.py`
steps (boot/GPIO, images, recovery); it does not automatically run all 58
peripheral cases. Its success does not validate this entire snapshot.

Next comes a separate automated campaign with an expected matrix and an
aggregator for local/CI reports. Preserve module, firmware and scenario SHAs,
ELF hash, tool versions, selected MCU/backend/OS, time, expected outcome and
evidence links. Missing reports and SKIP cannot yield PASS; count repeats
separately. Exclude serial numbers and personal paths from published data.

The latest attempt status and the last complete successful campaign count
can then be published separately in `ci-badges`, following
[stm32-cmake-yml](https://github.com/ViacheslavMezentsev/stm32-cmake-yml/blob/main/docs/ru/status.md).
Display the date and SHA; do not present old success as verification of new main.
A partial run must not replace the full result; a new failure must not be hidden
behind an old green count. Automation remains in [TODO](../../TODO.md).
