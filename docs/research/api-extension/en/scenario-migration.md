# Production scenario migration after API integration

[Research](index.md) · [Русский](../ru/scenario-migration.md)

2026-10-03. Working branch `codex/api-extension-research`, base `7ed6d0a`.
All current CMSIS scenarios across five profiles, HAL F030 and the minimal
consumer were checked. Core code, C firmware and API specification 0.2.2 did
not change. Development version 0.2.0.dev0; release, push and merge are separate.

## Changes

Reviewed 29 Python scenario/helper files. In 16 files, 44 groups containing
282 checks now use TECH-010: `(name, C expression, expected)` tables with a local
`_check_values` helper. A string expected value is a second C expression.
Evaluation remains actual, expected, check, stopping at the first failure.
Local helpers keep packaged scenarios standalone. Interleaved comments,
individual checks, injections, navigation and diagnostic report fields remain.
No new core table method is needed.

Five CMSIS profiles use `session.toml` → `target.toml` + `api.toml`.
New `HW_CI_ADC_SERIES` uses actual `Target.config`, `record/records`: five
consecutive ADC publications, sequence/provenance/range checks, mean and sample
standard deviation (`ddof=1`) for VDDA in mV and temperature in °C. External
configuration selects 2..20 samples; the journal limit is 32 records.
This checks the measurement chain and Python statistics, not calibration.
The journal remains runtime data; no export was added. GDB arithmetic over
saved data remains documented in [TECH-011](measurement-technique.md); this
production variant uses statistics.

HAL and the minimal consumer retain legacy configuration to check compatibility.
CI and `run_hw.py` full-image checks use a separate legacy descriptor: image
overrides cannot accompany a selected SESSION_CONFIG.

## Checks without hardware

- Original blocks from the base are preserved in `tests/host/scenario_tables.json`.
  `test_scenario_tables.py` compares complete call order before/after migration,
  including failures at every read and check in all 44 blocks.
- `test_measurement_scenarios.py` executes all five actual modules with the real
  Journal: numerical mean/stdev anchors, invalid count, stale sequence, quality
  and range failures. Failures produce no summary record; invalid count is
  rejected before MCU operations.
- Windows: 164 host tests, 153 PASS / 11 skips; research tests 91,
  90 PASS / 1 skip. Linux Docker: 164, 160 PASS / 4 skips.
- Docker format, host and GCC13 build/preflight for all five CMSIS profiles PASS.
  HAL build and 24 host/prepare checks PASS after updating provenance: the first
  run found the old digest of the migrated scenario. The original digest is
  retained. This was fixture metadata failure, not a hardware failure.
- Minimal consumer build and offline CTest 3/3 PASS.

## Hardware campaign

Windows, xPack GCC 13.3.1-1.1, GDB 14.2.90/Python 3.11.4.
F103 uses J-Link CE/SWD; other boards use ST-Link/OpenOCD/SWD.
Prepare preceded execution; ELF/manifest identities were verified.

| Profile | Production HW cases | Additional positive runs | Expected timeout ERROR |
| --- | ---: | ---: | ---: |
| CMSIS F030R8 | 19/19 | 5 | 1 |
| CMSIS F103C8 | 21/21 | 5 | 1 |
| CMSIS F401CC | 21/21 | 5 | 1 |
| CMSIS F411CE | 21/21 | 5 | 1 |
| CMSIS F429ZI | 21/21 | 5 | 1 |
| HAL F030 | 22/22 | 4 | 1 |
| Minimal consumer / F411 | 1/1 | 2 | 0 |

Total: 126 production cases (103 CMSIS, 22 HAL, one example). Separately,
31 positive repeats/restorations and six expected ERRORs. Repeats do not increase
the unique count. Every timeout verified scenario entry, TimeoutExpired, host
recovery and a successful subsequent scenario. ERROR remains in the reports.
Positive ADC/RTC cases followed injections (ADC runtime for HAL).

Final firmware: verified CMSIS on F030/F103/F429, verified consumer HAL on
F401/F411. Restoration BOOT/GPIO PASS, with `image_verified` and `reset_run`.
Serial numbers and local paths are not published. The F103 Flash warning remains:
profile 64 KiB, observed 128 KiB, image fits both. Macro preflight also contains
a GDB CP1252 → UTF-32 conversion warning; evidence retains it.

The [machine-readable report](../results/scenario-migration.json) includes every
stage status, checks, source/ELF/manifest/raw-report hashes, warnings and recovery.
Raw reports remain in local build directories. Reproduce with
`tests/api-extension/run_suite.py`: explicit `--session`, `--restore-session`,
`--stand`, and `--execute` for hardware; `--timeout-recovery` adds the negative
experiment. Without execute, only prepare runs. MCU mismatch and flash policy
other than if-different are rejected. Unexpected results stop the suite while
attempting restoration.

## Limits and next step

This is one local working-tree campaign, not verification of remote main.
The external consumer project was not fully migrated; only its previously
approved restoration firmware was used. Linux HW, GCC15, a new Orange Pi remote
run, RTOS and historical PoCs were not repeated. Hardware full-image stages of
`run_hw.py` were not exercised here; corresponding prepare checks ran in CI.

The first package is usable in production scenarios on the five checked MCUs.
Next: review these results and preparation for 0.2.0. These results do not
require adding other experimental methods to the core.
