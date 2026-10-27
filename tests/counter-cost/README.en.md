# Counters and observation cost

[Русский](README.md) · [TECH-024](../../docs/en/TESTING_TECHNIQUES.md#tech-024)

One neutral C++ source runs on host and Cortex-M3 in Renode. No core or board changes.
The eight-bit counter difference is valid only with complete samples, an independently
established upper increment below 256, in-range input and a delta within that bound.
250 to 5 with upper=11 yields 11; 7 to 7 with upper=0 yields valid zero; 0 to 255 is
valid with upper=255. A possible full wrap, missing data or inconsistent bounds yields
valid=0, not a measured zero. Real use also requires no reset/epoch change and a proven
rate/interval bound; two counter readings alone cannot establish those conditions.

The cost model assigns 7 teaching ticks per work unit and 3 per observation. Only the
first observation is inside the measured interval: empty baseline=3, total observer
cost=6; work=4 gives gross=31 and net=28. Empty work gives net=0. Starting at 250,
empty then work=4 leaves the clock at 34. Work above 16 is rejected without mutation.
These are specified model units, not DWT or measured CPU cycles. A constant baseline
is valid only under this fixed-cost model; hardware subtraction requires comparable
calibration and an uncertainty estimate. The model budget is declared before testing.

A separate scenario records six real GDB-call durations using host perf_counter_ns.
The first is a predeclared warmup; all raw samples, median and maximum of the remaining
five are retained. A separate analyzer requires exactly one complete record and
recomputes statistics; missing, duplicate or corrupt data makes the campaign ERROR
without rewriting the scenario PASS. This includes host/GDB/transport, not MCU execution time or WCET.
There is no latency acceptance threshold, only completeness and operation checks.

Three mutations: missing width mask, omitted baseline subtraction, missing eligibility
checks. Host verifies exact failures. Renode runs four cases for 1,2,3,0,0: 20 outcomes,
three intended FAILs and two corrected repeats. Original FAILs remain FAILs. Campaign
acceptance requires capture, ELF verification, verified cleanup and full POD restoration
in finally using the ELF symbol size, including failures. No peripheral recovery claim.

Run `python tests/counter-cost/run.py --host-only`, or add `--toolchain <ARM GCC root>`
and `--renode <Renode executable>`. Requires g++, Python 3.11+, GDB-Python, Renode 1.17.
Artifacts and hashes are in build/counter-cost/<id>. Windows Docker uses a source/build
volume, as described in [local CI](../../docs/en/local-ci.md).

API guidance: call once and inspect outcome/return_state/return_value (await in async).
Record raw data before check, including units, warmup and eligibility. Do not substitute
zero for unknown, repeat a side-effecting call just to read its result, or label sampled
maxima as WCET. DWT porting requires MMIO/SVD, availability/halt/sleep checks, saved
configuration and separately authorized hardware validation.

Validated 2026-10-27: four host variants on Windows/Linux; Renode 1.17 on both systems
produced 20 expected outcomes (17 PASS, 3 intended FAIL), including two corrected
repeats, with ARM GCC 14.2.1 / GDB 15.2.90. All five transport records per campaign
passed independent completeness/statistics analysis; capture and POD restoration
were verified for every scenario. This is neither hardware acceptance nor WCET.
