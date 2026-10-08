# Result export and evidence index

[Documentation](index.md) → Results · [Русский](../ru/RESULTS.md)

Available in Unreleased. These are external host commands: they read saved files, never start GDB or
access the MCU, and add no Target methods. Existing scenarios need no migration. Enable
[journal capture](API.md#result-journal-capture-unreleased) when running scenarios.

## What is exported

`record(name, data)` stores **arbitrary data**, not only measurements. name is an author label,
not a built-in type. sequence is insertion order, not time. Three distinct roles:

| Role | Contents |
| --- | --- |
| Generic journal | All sequence/name/data entries, preserving original types |
| Projection | Optional fields selected explicitly in export.toml |
| Index | Runs/files: paths, sizes, hashes, integrity; no interpretation of data |

```python
t.record("adc.sample", {"vdda_mv": 3295})
t.record("fsm.transition", {"from": "idle", "to": "running"})
t.record("diagnostic", {"message": "channel unavailable"})
```

All entries remain in generic export. Projecting adc.sample never deletes other entries. Units,
time and semantics are never inferred from field names.

## Explicit campaign selection

Create selection.json; file paths are relative to the separately supplied evidence root:

```json
{
  "schema": 1,
  "campaign_id": "board-bringup-001",
  "name": "Initial board checks",
  "runs": [
    {
      "result": "run-001/result.json",
      "stand": "f411-lab",
      "artifacts": {
        "elf": "run-001/firmware.elf",
        "junit": "run-001/junit.xml"
      }
    }
  ],
  "packages": []
}
```

schema=1, name and runs are required; omitted campaign_id generates a UUID. packages is optional;
entries are `{"path": "input.zip", "sha256": "<64 lowercase hex digits>"}`.
Each run requires result/stand; artifacts is optional, roles result/records are reserved. Report
and saved records.json are included automatically; other files are explicitly selected. No build
scanning. Only relative POSIX paths without .., backslashes, colons or symlink components are accepted.
stand is an external label, never inferred from a probe serial number.

run_id comes from the report. Legacy reports may use assigned_id with identity_source=assigned.
Missing identity leaves a null field and diagnostic. Source reports are never rewritten; assigned IDs
do not invent compatible missing journals. Repeated case_id remains visible; duplicate run_id or
conflicting assigned_id refuses the entire build.

## Commands

```text
python -m stm32_gdbtest results export --root build/evidence --selection selection.json --output build/export-001
python -m stm32_gdbtest results export --root build/evidence --selection selection.json --output build/export-002 --config export.toml
python -m stm32_gdbtest results verify --root build/evidence --index build/export-001/index.json --output build/integrity-001.json
```

Export directory and verify file must be new. --config applies only to export. Export creates:

- index.json: runs and selected files;
- export.json: sources, generic records, projections, diagnostics, series definitions;
- records.csv: run_id_json, case_id_json, sequence, name_json, data_json;
- measurements.csv: only with --config; raw/transformed values and state;
- summary.json: separate index/export codes, command code and limits;
- selection.json, source-hashes.json and optional export.toml: processing inputs/provenance.

Evidence itself is not bundled. Index paths stay relative to --root, not the index.json location.
This is a processing bundle, not a replacement for pack.

## Explicit projections

```toml
schema = 1

[[series]]
name = "vdda"
record = "adc.sample"
path = ["vdda_mv"]
unit = "V"
scale = 0.001
```

record matches exactly. path is an array of dictionary keys; empty selects all data; dots inside keys
are literal. name must be unique; unit is explicit. Without scale/offset, the selected type is retained,
including bool, strings and containers. Explicit `value * scale + offset` accepts only int/float, not bool;
defaults are 1 and 0. Invalid arithmetic or nonfinite output gives error. No Python/GDB expressions run.

| State | Meaning |
| --- | --- |
| value | Found; raw_value and value present |
| null | Explicit None/null; both values null |
| missing | Absent key; values absent |
| error | Traversal through a non-object or failed transformation; reason retained |

No matching records is diagnosed. missing/error give code 2; null alone is valid. Zero, false and null
are distinct. JSON preserves types and large integers. CSV values are JSON literals: empty cell means
absent field, null means explicit null. Arbitrary text cells are JSON-encoded, including formula-like
strings. Excel may auto-convert values; CSV roundtrip requires JSON-decoding cells. JSON, not Excel,
provides the type-preservation guarantee. No timing or mean/standard-deviation aggregation is added.

## Integrity and outcomes

ok matches a reference hash; missing denotes absence; changed denotes mismatch; unverified is an
initial snapshot without a previous reference. It can establish a verify baseline, not prove earlier
integrity. Hashes do not authenticate authors. executed_from comes only from result.package.sha256,
checked against selected ZIPs; matching ELF is insufficient. Capture metadata is opaque; the journal
itself is validated for schema, identity and hash before export.

Utility code is 0 or 2, **not a campaign verdict**. Scenario FAIL/ERROR still permits valid journal export.
Original status/command_code/capture are retained. Prepare is indexed without journal export.
Source errors do not hide valid sources; a diagnostic bundle is published with code 2. selection_indices
maps exporter positions to the selection. Unknown legacy information is null, never fabricated.
SKIP is read separately; no runtime skip mechanism is added. Verify checks files and does not annul
historical index/scenario errors. unverified alone is not an error.

## Limits and publication

| Argument | Default |
| --- | ---: |
| --max-runs | 128 |
| --max-files | 2048 |
| --max-input-bytes | 268435456 (256 MiB) |
| --max-output-bytes | 67108864 (64 MiB) |
| --max-series | 32 |

All limits are positive integers. Input JSON: 16 MiB; export.toml: 64 KiB. Streaming counters bound
file reads; verify counts each artifact entry, including duplicates. The conservative pre-projection
estimate `bytes(records) * (4 + 3 * series_count)` can refuse before actual output reaches the limit.
Actual written bytes are also bounded. These are utility limits, not scenario API limits. Data is
processed in memory; byte limits are not process RSS limits.

Index/export read a temporary snapshot; original hashes are rechecked before publication. Detected
changes, exceeded limits or write failures cancel publication. Inputs are not locked: the selection
is not a transaction across concurrently changing files. A completed directory is renamed on the same
filesystem; verify publishes a completed file by hard link, refusing unsupported filesystems. There is
no partial direct write into the final destination. Commands use <output>.lock with PID; other writers
to that destination are unsupported. A crash may leave the lock; confirm its process exited before
removing that specific lock. Another writer's lock is never auto-removed. No power-loss durability guarantee.

## JSON/HTML summary (Unreleased)

```text
python -m stm32_gdbtest results report --root build/evidence --index build/export-001/index.json --output build/report-001 --theme auto
python -m stm32_gdbtest results report --root build/evidence --index build/export-002/index.json --export build/export-002/export.json --output build/report-002 --theme light
```

Creates a new directory containing campaign.json, campaign.html and integrity.json. --root is required:
files are rechecked before generation, with the check time in the report. This is neither live monitoring
nor a new hardware run. Limits/output ownership match export; a partial directory is never published.

Scenario verdict, run command_code, capture, current file integrity and export diagnostics are separate.
hardware/prepare/unknown groups retain every attempt in selection order within each group. Repeated
case_id is not collapsed. SKIP is not PASS; unknown outcomes appear as UNKNOWN with their original value
in details. aggregate_verdict is always null.

Optional --export adds per-attempt generic record/projection counts and diagnostics. Selection, IDs,
source hashes and record sequences must agree; mismatched or incomplete exports are refused before
publication. This checks consistency, not authenticity. Export data describes its original snapshot;
current integrity may already show changed. Without --export, data is shown as “—”, not zero.
Prepare never requests a journal.

Report code is the maximum of index, fresh integrity and optional export codes: 0 or 2. It describes
evidence processing, not a campaign verdict. Scenario FAIL/ERROR can still yield a successfully
produced report; original PASS with capture.error remains independently visible. Data errors produce
a complete diagnostic report with code 2; invalid schema/linkage or publication failure leaves no final
directory. Invalid run identity is never repaired by merging attempts.

--theme accepts auto (system preference), light or dark. HTML is standalone: no JavaScript, external
fonts, network resources or automatic file links. Shared light/dark report palettes, native details
controls and horizontally scrollable wide tables are used. All user strings are escaped. campaign.json
is available for external consumers. JSON input limit remains 16 MiB, including --export; omit an oversized
export and generate an index-only report instead. Nested details are displayed, never executed.
