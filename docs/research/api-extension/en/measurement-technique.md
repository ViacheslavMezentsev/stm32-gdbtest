# TECH-011: acquire → record → calculate

[Research](index.md) · [Русский](../ru/measurement-technique.md)

[TECH-010/011 hardware pairs on F030/F103/F411](techniques-three-boards.md): 7/7 HW and 7/7 prepare each; original checks preserved, restoration PASS. F103 Flash warning retained. Research facades, not core integration.

2026-10-03. Combines the earlier VDDA/temperature series with accepted record/records/
config contracts. The [paired variant](../../../../tests/api-extension/measurement_technique.py)
uses research RecordingTarget/ConfiguredTarget; production rc.2 lacks these operations.
This stage adds no new public API.

## Pair preparation

Control: [original E1 series](../../../../tests/api-extension/measurement_series.py).
configured_series reads api.toml settings:

```toml
schema = 1
[records]
max_records = 128
[user.measurement]
count = 10
expected_quality = 2
```

expected_quality=2 applies to the relevant calibration variant, not every MCU.
API does not interpret user; the scenario validates count (2…100 for this pair).
Journal capacity includes the summary: N samples need at least N+1 entries plus
sufficient node/text budgets. Rejection is not hidden by truncating the series.

Order preserved: reach board_adc_sample → reach board_delay_ms → counter →
quality/vdda_mv/temperature_mdeg_c → record → assertions. Consecutive uint32
counters must advance exactly once. Repeated/missing samples, bad quality or range
stop execution. A bad sample is recorded before its assertion but no summary is
produced. Journal sequence does not replace the MCU acquisition counter.

Consistency comes from the application's publication protocol: fields must already
be published and not changing under DMA/another core at the stop point. Halt or a
single counter alone does not establish atomicity. Other applications need their own
consistent-read protocol; MMIO FIFO/read-to-clear does not transfer automatically.
Debugger stops affect measurement timing.

## Calculations

Read records once after collection. Ordinary Python data supports mean/stdev/min/max,
filtering and channel comparisons without rereading MCU. Preserve units, count and
sample-standard-deviation semantics (ddof=1, N≥2); pstdev describes a population.
Low variance does not establish calibration accuracy. Die temperature is not ambient.

```python
from statistics import mean, stdev

samples = [r['data'] for r in t.records('mcu.measurement')]
if len(samples) != expected_count or len(samples) < 2:
    raise ValueError('incomplete measurement series')
vdda_mv = [s['vdda_mv'] for s in samples]
temperature_c = [s['temperature_mdeg_c'] / 1000 for s in samples]
t.record('mcu.summary', {
    'count': len(samples),
    'vdda_mean_mv': mean(vdda_mv),
    'vdda_stdev_mv': stdev(vdda_mv),
    'temperature_mean_c': mean(temperature_c),
    'temperature_stdev_c': stdev(temperature_c),
    'ddof': 1,
})
```

Validate freshness/quality before this fragment, as in the paired variant. If rejection
of samples is allowed, define rules beforehand, retain reasons/counts and require a
minimum accepted count. Never silently filter failures to obtain PASS or replace missing
values with zero.

### GDB operation on captured data

mean_in_gdb transfers integer sum/count via convenience variables and evaluates the
fixed expression `(double)$ddtt_tech011_sum / $ddtt_tech011_count`. It contains no MCU
addresses, firmware calls or continue. Values use gdb.Value, not interpolation into
arbitrary commands. Scratch variables are saved and restored in finally; invoke on
the main GDB thread only. This implementation requires a nonempty integer series and
a signed64 sum. Double can round large integers. Python is simpler for an ordinary mean.

This demonstrates GDB arithmetic, not a general journal-driven command executor.
Using the result for set_value/function calls/register changes is a separate explicit
intervention phase with validation/restoration. Captured samples do not become current
MCU state during such an operation.

## Evidence and boundaries

[Five paired cases](../../../../tests/api-extension/test_measurement_technique.py):
normal series, uint32 wrap, duplicate, gap and bad quality. reach/value/check traces
and results match original E1. Existing numerical anchors: 3200/3300/3400 mV → mean
3300, stdev 100; 24/25/26 °C → mean 25, stdev 1. Additional tests verify scratch
restoration on failure and invalid aggregates rejected before GDB access.

Real GDB14/GDB16 each passed four numeric sets, including negative values and a
fractional mean, with scratch restoration verified.
[GDB14](../results/series-gdb14.json), [GDB16](../results/series-gdb16.json).
No ELF/MCU: this is not repeated hardware acquisition. Earlier hardware evidence:
[E1](e1.md), [F0/F1](portability.md); it does not establish new integration.
Windows: 88 tests, 87 PASS/1 CMake skip.
Linux Docker: 88/88 PASS; CI documentation: 4/4 PASS.

Next: combine TECH-010/011 pairs into a stand comparison plan; first enforce and
verify already approved prototype configuration upper bounds. Core and production
scenarios remain unchanged.
