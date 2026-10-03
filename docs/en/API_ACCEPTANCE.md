# Accepted API: results and reproducible checks

[Documentation](index.md) · [Русский](../ru/API_ACCEPTANCE.md)

This is a public summary of accepted behavior and acceptance, not a development diary.
Contract: [API specification](../TECHNICAL_SPECIFICATION_API.md); guide: [API](API.md).

## Accepted package

record/records and RecordError provide a per-invocation journal of copied ordinary
Python values with atomic limit failures. config/config_props expose immutable
selected configuration and its provenance. session.toml links external files;
SESSION_CONFIG is explicit. Legacy operation remains supported.
Journal export, additional frame/context operations and adaptive scheduling are excluded.

## Verified scenarios

Campaign dated 2026-10-03, working tree based on 7ed6d0a: CMSIS F030R8 19/19;
F103C8/F401CC/F411CE/F429ZI each 21/21, total 103. HAL F030 22/22,
minimal consumer 1/1. Windows, GCC13, GDB14; F103/J-Link, other boards
ST-Link/OpenOCD. Restoration BOOT/GPIO PASS. F103: profile Flash 64 KiB,
observed 128 KiB, image fits both. Separately: 31 positive repeats/restorations
and six expected timeout ERRORs. This is bounded historical evidence, not coverage
or verification of every later SHA.

44 table blocks (282 checks) have paired host regression for call order and first
failure: tests/host/test_scenario_tables.py. Five production
[test_measurements.py](../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py)
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
