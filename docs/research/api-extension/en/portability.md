# E1–E4: portability to F0 and F1

[Study](index.md) · [Русский](../ru/portability.md)

On 2026-10-03 the experiments were extended before API acceptance. The core is
unchanged; only research scenarios and the runner changed. Source baseline:
6da79d5 plus the portability changes in the accompanying commit.
[Sanitized evidence](../results/portability-f0-f1.json) includes ELF/manifest hashes,
checks, snapshots, measurements and warnings. Raw logs remain local.

Change validation: Docker docs/host 5/5 PASS; 114 host tests (4 platform skips);
44/44 research host tests PASS. Two adapter tests check the current revision
and rejection of a third-component change without revision history.

## Setup and outcome

| Board / profile | Connection | Prepare | Hardware runs |
| --- | --- | --- | --- |
| Nucleo-F030R8 / STM32F030R8T6 | Windows, ST-Link/OpenOCD, SWD 1000 kHz | 8/8 PASS after rebuilding | 8/8 PASS |
| WeAct BluePill-Plus / STM32F103C8T6 | Windows, J-Link CE/J-Link, SWD 1000 kHz | 8/8 PASS | 8/8 PASS |

Both runs used GDB 14.2.90.20240526-git from xPack GCC 13.3.1 and the existing
tests/firmware CMSIS firmware. Eight runs comprise two baselines (ADC units,
Sleep/SysTick), four experiments (measurements, read, context, finish), and two
restoration checks (BOOT/GPIO). Every run verified the image and reset_run.
Both boards retain the checked CMSIS firmware. F411 was not rerun; E1–E4 retain
its historical results.

The first F0 prepare returned ERROR before connection: the stale ELF lacked
adc_convert_f030. Rebuilding the existing F0/F1 projects resolved it; the error
is retained in JSON. Every F1 hardware run warns that profile Flash is 64 KiB
while the observed capacity is 128 KiB; the image fits both. PASS neither proves
the exact chip marking nor expands the profile.

## Consumer parameters

| Consumer fact | F0 | F1 | F411 (earlier) |
| --- | --- | --- | --- |
| RAM upper bound | 0x20002000 | 0x20005000 | 0x20020000 |
| NVIC banks used | 1 | 2 | 2 |
| Measurement quality | 3: single-point calibration | 1: typical parameters | 2: factory calibration |
| Hardware breakpoint budget / guards | 4 / 1 | 6 / 4 | 6 / 4 |

These are technique parameters in board_config.py and the profile, not universal
properties of record/read/context/finish. Budget exhaustion now fills the remaining
profile budget. F0 does not access a nonexistent second NVIC bank. The paired E1
ADC comparison remains a separate F411 experiment, excluded from `--case all`.

## Observations

| 10 measurements within one scenario | F0 | F1 |
| --- | --- | --- |
| VDDA mean / sample SD, mV | 3307.4 / 0.966092 | 3313 / 0 |
| Temperature mean / sample SD, °C | 33.6172 / 0.115013 | 24.1802 / 0.097083 |

SD uses N−1. Zero SD of quantized readings does not imply zero measurement error;
absolute temperature accuracy cannot be compared across quality modes.

Read retained types and snapshot history and matched ordinary reads. Context on
both boards captured SysTick → signal → board_delay_ms → app_loop → main. Stack
termination remained incomplete: `older=None`, `NO_REASON`, currently labelled
`unwind_error`. This supports Q8, not a claim of stack corruption. Close left zero handlers.

Finish returned unsigned long=1 and void on both boards; a foreign breakpoint
produced interrupted without a value. Budget refusal and guard preservation passed.
Other ABIs, signed/float/aggregate, fault and an operation-specific timeout remain untested.

## E5/E6 implications

Three tested configurations strengthen evidence for limited prototypes but do not
resolve [E5](e5.md) findings. Its matrix remains applicable with the additional
F0/F1 evidence and limitations above. Accepting record/records first remains a proposal.

Next: discuss Q1–Q16 and extension contracts against the separate
[API specification 0.1.0](../../../TECHNICAL_SPECIFICATION_API.md), which describes
only current rc.2. Document revision has three components; API_VERSION remains 1.
Core integration and scenario migration still require the owner's decision.
