# Accepted API: results and reproducible checks

[Documentation](index.md) · [Русский](../ru/API_ACCEPTANCE.md)

This is a public summary of accepted behavior and acceptance, not a development diary.
Contract: [API specification](../TECHNICAL_SPECIFICATION_API.md); guide: [API](API.md).

## 0.3.0 package

API specification 0.3.6, general specification 0.68. `profile` (project data, build facts, case, stand, GDB)
replaces `config`/`config_props`; one `check` with matchers and a table, `refused`, `write(rows)` with an
expression as the value, `symbol`, `memory`, `locals`/`arguments`, C strings, navigation (`reach`, `finish`,
`step`, `until`, `watch`, `Point`), `ret`, `call`, `reset`, `execute`. A shared scenario directory with nine
showcase scenarios; the techniques are described in the [techniques catalogue](TESTING_TECHNIQUES.md).

Campaigns of 2026-10-05, five boards (F030R8 and F401CC/F411CE/F429ZI — ST-Link/OpenOCD, F103C8 — J-Link),
full suite: F030R8 48 scenarios, the others 50 each.

| Scheme | Runner and GDB → server | Outcome |
| --- | --- | --- |
| Local on Windows | Windows, GDB 14.2.90/15.2.90/16.3.90 (xPack 13.3.1/14.2.1/15.2.1) | 15 of 15 suites PASS |
| Local on a Linux stand | Orange Pi 5, Ubuntu 20.04 aarch64 | 5 of 5 PASS |
| Remote server | Windows → Orange Pi 5 over SSH | 5 of 5 PASS |
| Remote server | WSL2 → Orange Pi 5 over SSH | 5 of 5 PASS |
| Prepared-run package | built in WSL2, run on the Orange Pi 5 | 5 of 5 lifecycles at 10/10 |
| GitHub hardware CI | packages of the `prepare` job (ubuntu-24.04), run on the Orange Pi 5 self-hosted runner | 5 of 5 lifecycles at 10/10 |

In every suite the only non-PASS is the intended `timeout` check with its expected ERROR. The Linux-stand runs
found and closed two problems: a Cortex-M0 watch point stopping in a function epilogue (`HW_CI_WHO_WRITES`)
and a busy server port on the stand host (general specification 0.68). The F030 HAL fixture check without a
board, `python ci/run_checks.py hal`, passes. The package schemes check the lifecycle: build, prepare, boot, strict
identity, full and partial flashing, an image verification refusal, a timeout and the recovery.

## First package: record/records and config

Historical 0.2.0 acceptance; in 0.3.0 `profile` replaces `config`/`config_props`.


record/records and RecordError provide a per-invocation journal of copied ordinary
Python values with atomic limit failures. config/config_props expose immutable
selected configuration and its provenance. session.toml links external files;
SESSION_CONFIG is explicit. Legacy operation remains supported.
Journal export, additional frame/context operations and adaptive scheduling are excluded.

## Verified scenarios of the first package

Campaign dated 2026-10-03, working tree based on 7ed6d0a: CMSIS F030R8 19/19;
F103C8/F401CC/F411CE/F429ZI each 21/21, total 103. HAL F030 22/22,
minimal consumer 1/1. Windows, GCC13, GDB14; F103/J-Link, other boards
ST-Link/OpenOCD. Restoration BOOT/GPIO PASS. F103: profile Flash 64 KiB,
observed 128 KiB, image fits both. Separately: 31 positive repeats/restorations
and six expected timeout ERRORs. This is bounded historical evidence, not coverage
or verification of every later SHA.

44 table blocks (282 checks) have paired host regression for call order and first
failure: tests/host/test_scenario_tables.py. Five production
[test_measurements.py](../../tests/firmware/common/tests/board/test_measurements.py)
scenarios use config, record/records, mean and sample stdev. Numerical anchors and
negative cases: tests/host/test_measurement_scenarios.py.
Reproduce HW suites with [run_suite.py](../../tests/firmware/run_suite.py): explicit
session, restore-session and stand; without execute only prepare runs.

Current release acceptance is in [RC020_READINESS](RC020_READINESS.md).
Historical campaigns and release lifecycle are counted separately.

## Journal cost regression

The public [benchmark](../../tests/benchmarks/measure_records.py) uses only core code.
From the root: `python tests/benchmarks/measure_records.py build/records-cost.json`.
In GDB-Python, import the module by path and call run with the output path; no ELF,
server or MCU is required. Outputs remain local.

13 shapes: 10/128/1024 measurement pairs, lists with 4096/32768 nodes,
65536/524288-byte text, Unicode near 65536 bytes, a 4096-node dictionary,
depths 8/32 and 256/1024-bit integers. Five exact boundaries and atomic rejection
of excess are checked. After warmup: nine batches of ten operations, GC enabled;
compare medians of write/read batch means. Save an accepted-version baseline in
the same environment and compare the new implementation; investigate >2× slowdown
under API specification 6.5. These are not worst-case latency or RSS guarantees.
tracemalloc and reachable-object size are measured separately with preallocated inputs.

Initial integration passed in CPython and GDB14/GDB16: 13 shapes and five boundaries
per environment, without >2× regression. This is integration evidence, not portable
absolute timing. Standard records host tests check contractual limits independently.

## Composite technique and example verification — 2026-10-09

A separate series, not a recount of historical API acceptance: the three common scenarios
`HW_CI_EVENT_INTERVALS`, `HW_CI_WAIT_CHANGES`, `HW_CI_EVENT_INJECTION` passed 18 prepare and 18 HW runs.
The standalone `HW_CPP_CONTEXT` passed 12 builds, 12 prepare and 12 HW runs (Og/O2).
Boards: F030R8, F103C8, F401CC, F411CE, F429ZI through OpenOCD and AT32F403A through J-Link.
Original CI images were restored after both series: 24 BOOT/GPIO PASS, image_verified=true,
teardown=reset_run. GCC 14.2.1, GDB 15.2.90.20241130-git/Python 3.12.8, OpenOCD 0.12.0, J-Link 8.32.

Limits: nominal ticks do not establish timing accuracy; watchpoint IDs may be inferred.
C++ arguments remained available at O2; no hardware optimized-out case was observed.
The published wait scenario does not include an intentional timeout.
[Technique catalogue](TESTING_TECHNIQUES.md), [C++ example](../../tests/cpp-context/README.en.md).
