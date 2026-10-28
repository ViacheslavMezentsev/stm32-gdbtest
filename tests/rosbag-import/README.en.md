# Offline ROS1 bag v2 import (A6)

[TECH-026](../../docs/en/TESTING_TECHNIQUES.md#tech-026) · [Русский](README.md)

The first real external-evidence adapter: a saved ROS1 bag v2 recording is turned
into a neutral set of channels and samples, and a separate analysis decides whether
it can be related to a debugger snapshot. No new capture, MCU, GDB or Renode is needed;
the `stm32_gdbtest` module is unchanged. Python 3.11+ only, no third-party libraries.

## Contents

| File | Role |
| --- | --- |
| `rosbag1.py` | Strict bag v2 reader: uncompressed and bz2 chunks, index cross-check, std_msgs |
| `importer.py` | Format adapter: topic → channel with declared units, record time with an explicit clock source |
| `analysis.py` | Separate verdict: completeness → identity → clocks → channels → anchors → GDB moment → values |
| `fixture.py` | Synthetic bag v2 for CI and its corrupted copies |
| `run.py` | Synthetic campaign or local import of a real recording |

The reader never returns partial data: a truncated file, `index_pos=0` (recording not
closed), chunk info/index data disagreeing with the messages, unknown compression
(lz4 included) or extra message bytes give `import_invalid` with a reason.
A type is decoded only when both the name and the definition md5 match; otherwise
the channel stays undecoded and cannot be compared.

## Time

`ros1_record_time` is the receive time on the recording host (unix, ns). It is neither
the MCU clock nor the GDB read moment; the recording host and the scenario PC may be
different machines. Anchors are built by the analysis from an MCU counter channel
(for example uptime in seconds, the same tick source as the debugger snapshot).
A k−1 → k transition gives the interval (last receive of k−1, first receive of k).
A snapshot with tick T, k = ⌊T/1000⌋, lies in
`[last receive of k − latency, first receive of k+1]`. Without both transitions in one
segment the result is `moment_outside_anchors`; a counter decrease (reset) starts a new
segment, and a match in several segments gives `moment_ambiguous`.

Delivery latency must be bounded: `basis=measured` for a real recording, `fixture` only
for synthetic data. An assumed latency gives `clock_assumed` even when values agree.
Sequential rostopic samples in records are not treated as simultaneous with each other
or as matching the bag, and the analysis does not use them.

## Values

A channel agrees when every sample received within the interval of the possible moment
(plus latency) matches the snapshot within tolerance; all outside tolerance is FAIL;
a mix is `time_boundary`. A repeated constant value is not a duplicate by itself.
ROS and GDB read the same firmware state: agreement of two transports checks delivery
and timing, not an independent measurement (`independence=same_firmware_state`).

## Synthetic campaign

```sh
python tests/rosbag-import/run.py
python tests/rosbag-import/analysis.py build/rosbag-import/<campaign>/normal
```

23 experiments with expectations fixed before the run: three PASS (uncompressed, bz2,
repeat), one FAIL (value outside tolerance with full timing certainty) and 19 UNKNOWN.

| Reason | Experiments |
| --- | --- |
| `import_invalid` | truncated file, no index, index mismatch, lz4 |
| `channel_contract` | other type, foreign md5, renamed topic, other units |
| `nonfinite_value` | NaN in a compared channel |
| `identity` | other experiment in metadata, other message count |
| `clock_shift` | bag time outside the record window |
| `clock_unqualified`, `clock_assumed` | no MCU counter; latency not measured |
| `moment_outside_anchors` | debugger halt, then reset: no k+1 transition |
| `moment_ambiguous` | reset: the same tick in two segments |
| `time_boundary` | the value changes inside the interval |
| `snapshot_missing`, `scenario_not_pass` | no snapshot; scenario not PASS |

Every experiment keeps `source.bag`, `manifest.json`, `import.json`, `samples.jsonl`,
`capture.json`, `scenario.json`, `records.json`, `analysis.json` and `sha256.json`.
Re-analysis reads only the files and checks the hashes. Analyzer: exit 0=PASS,
1=FAIL, 2=UNKNOWN; run.py: 0 when the whole matrix matched.

## Real recording

```sh
python tests/rosbag-import/run.py --bag <rec>.bag --capture <rec>.json \
  --result <ddtt>/result.json --records <ddtt>/records.json --contract <local-contract>.json
```

The contract (channels, units, tolerances, anchor and expected outcome) and the data
stay local; `capture.json` receives only the experiment, record window and bag summary,
without port or serial numbers. Source files are only read.

Checked on 28.10.2026 with an F411 telemetry recording (Windows and Linux): 63 channels
and 13,776 messages were imported completely and the summary matched the metadata.
Two segments (reset at session end) and a 13.8 s pause (target halted by the debugger)
were found. The GDB snapshot was taken at tick 27,044 ms, after the last 26 s transition;
there is no 27 → 28 transition before the reset, so the outcome is
`UNKNOWN moment_outside_anchors`. This is the expected boundary: without publications
after the read the snapshot moment is not tied to bag time, and delivery latency was not
measured. The "debugger minus ROS" numbers in records are not confirmed by this analysis.

## Boundaries

MCAP from Android and the radio simulator are the next sources; the neutral channel and
sample format is designed for them, but those adapters are not implemented. Physical
clock synchronisation, latency measurement and DDTT eligibility of a real recording
need a separate experiment. The JSON files are the example's local format, not a public
result schema.
