# Journaling

[Documentation](index.md) · [API](API.md) · [Results](RESULTS.md) · [Русский](../ru/JOURNALING.md)

## Availability

This guide describes release 0.6.0; release 0.5.0 lacks these extensions.
A2, A3.1 and A3.2 journal enforcement are implemented. Schema 3 permits journal error/truncate.
Schema 3 journal/report quotas and independent error/truncate policies are executable.

## Sources and output

Records contains named measurements and MMIO/execution audit; result contains verdicts,
checks/stops/mutations/evaluations/executions/resets, completeness and cleanup. Summary is
a derived navigation aid with source hashes, not primary evidence. Console/JUnit output
is presentation. Full/compact storage preserves logical events; full/failures/summary
output does not change check execution. In session.toml, [results] capture=true saves
records.json. Analyze it with its matching result.json. print does not replace record.

## Configuration

A working lossless configuration uses schema=2, [journal] representation="compact",
and [report] representation="compact", console="summary". Existing [records] budgets
remain configurable. Schema 3 additionally accepts journal.on_limit and report.on_limit
(error or truncate, independently, default error) and report.max_rows_per_collection.
It fills explicit defaults: representation=full, console=full, on_limit=error.

| Budget | Schema 3 default | Maximum |
| --- | ---: | ---: |
| records.max_records | 4096 | 65536 |
| records.max_nodes | 131072 | 2097152 |
| records.max_text_bytes | 1048576 | 16777216 |
| records.max_depth | 16 | 32 |
| records.max_integer_bits | 256 | 1024 |
| report.max_rows_per_collection | 65536 | 65536 |

Minimum 1; booleans, floats, strings, zero, negatives and values above maxima are rejected.
No unlimited setting. Unknown keys in schema 3 records/journal/report are rejected.
Other application sections remain opaque data, not recognized journaling settings.
Schema 1/2 defaults and fingerprints are unchanged and reject the new policy keys.
The runner exposes effective settings in api_policy. Capsules and packages carry hashed
source TOML; receivers revalidate values and the defaults/bounds/policies fingerprint,
without reopening original paths. API schema and capsule/artifact schemas are independent.

## Fixed safety limits

Accumulation budgets are not RSS limits. Defensive bounds remain fixed: records file
64 MiB, result file 16 MiB, result expansion 64 MiB, block/materialization/deferred-value
limits; summaries 1 MiB, 100 groups and 20 references/group. The evidence diagnostic
reserve holds 16 bounded details/64 KiB JSON. Raising max_records does not bypass other
limits. Do not patch implementation constants from application scenarios.

## Scenario routes

| Route | Behavior and boundary |
| --- | --- |
| inspect / prepare | Offline validation; no target execution evidence |
| pack / open | Snapshot transport; execution admission checks supported policies |
| def / checks and navigation | Completed checks count independently of stored rows |
| async def / live window | Execution audit is separate; wait timeout does not halt |
| MMIO | Attempt/result audit; missing result never proves success or no effect |
| Caught CheckFailed | Failure remains in independent accounting |
| Exception / cleanup | Primary errors, audit and cleanup are distinct; requested cleanup is not verified recovery |
| Offline reader | Saved bytes are not necessarily complete observations |

A3.1 evidence stores attempted/saved/lost and loss boundaries; check_accounting retains
executed outcomes. Missing rows cannot erase FAIL. Incomplete evidence gives command=2,
partial summaries and blocked DDTT confirmation. Compact collection complete refers to
stored rows; also inspect evidence.stores. Legacy metadata absence is not a new guarantee.
The reserve omits user payloads; after exhaustion it counts omitted diagnostics. Existing
A1 fields remain for compatibility. Process/memory/disk failures cannot guarantee publication.

## Explicit journal truncation

In 0.6.0, API schema 3 executes `journal.on_limit="error"|"truncate"`.
The `[records]` budgets bound accumulation. Exhausting records/nodes/text_bytes under
truncate preserves whole prefix records and stops detailed storage until scenario end.
Checks, MMIO, live execution and cleanup continue. Completeness becomes `truncated`,
without changing the scenario outcome by itself: PASS with command=2, SAVED capture
and partial analysis is possible. Incomplete runs cannot confirm DDTT claims.

`records(name=None, *, require_complete=True)` raises `RecordError`/`incomplete_evidence`
for an incomplete journal, including named queries. Explicit `require_complete=False`
returns the stored prefix with original sequence numbers; it does not certify completeness.
Invalid types, cycles, depth, integer width and hard validation resource ceilings are
errors, not truncation. Inputs remain validated after detailed storage stops.

MMIO descriptors and attempts commit atomically. An attempt whose result did not fit
proves neither success nor absence of effects. Truncation adds no register reads/writes.
Transport/storage errors are not suppressed. The first loss cause, attempted/saved/lost
and first_lost/last_lost remain in evidence; diagnostic storage remains bounded.

Truncate policy uses evidence schema 2, result schema 3 (full/compact), and records
schema 3 with completeness checked against result. Old readers reject these formats.
Use the module shared readers. Report quotas/truncation are executable too; see the section below.

Inspect configuration offline, select budgets, enable capture, then assess scenario,
command, capture, evidence and cleanup separately before evaluating DDTT applicability.
Examples: tests/renode-backend/run_report.py; host tests: test_evidence.py and
 test_policy_config.py; tests/renode-backend/run_journal.py and test_journal_truncate.py. An intentional ERROR checks the tool contract, not MCU behavior.

## A3.2: report quotas and truncation (0.6.0)

API schema 3 applies report.max_rows_per_collection independently to checks, stops,
mutations, evaluations, executions and resets, in full and compact storage. Range:
1–65536, default 65536. report.on_limit="error" refuses overflow; "truncate" preserves
each collection prefix without stopping other collections, journal, checks or cleanup.
Journal/report policies are independent; all validated combinations are executable.

Attempted continues increasing, saved is the prefix length, lost and first_lost/last_lost
identify the omitted tail. The bounded reserve retains the first cause per collection.
Independent check_accounting counts all outcomes: catching exceptions or dropping rows
cannot erase FAIL. Summary groups describe saved rows; check_accounting retains full
outcome counts. Scenario PASS is possible, but command=2, analysis=partial and DDTT
confirmation is blocked.

Only the row quota is suppressed, never spool, serialization, transport or recovery
errors. If the saved prefix cannot be read/published, state becomes unavailable while
the initial truncation cause and independent counts remain. Dropped payloads are not
materialized: no repr or lazy GDB read is invoked for an omitted row. Missing rows
therefore do not certify the validity of their values.

Report truncation uses evidence schema 3 (report-truncate/both-truncate), result schema 3
and records schema 3. Readers unaware of this evidence schema reject it. Journal-only
truncation retains evidence schema 2; legacy strict formats remain readable. Report
truncation does not make a complete journal incomplete: records() checks journal
completeness, whereas whole-run analysis considers every store.

```toml
schema = 3
[journal]
representation = "compact"
on_limit = "error"
[report]
representation = "compact"
console = "summary"
on_limit = "truncate"
max_rows_per_collection = 1000
```

This explicitly selects a partial report. For complete acceptance evidence, keep error
and choose a sufficient budget. Example: tests/renode-backend/run_report_quota.py;
regressions: tests/host/test_report_truncate.py. No physical boards are involved.

## A3.3: consumers of incomplete evidence

`results export` checks all stores before projection. Incomplete sources produce no
records.csv/measurements.csv rows: diagnostics and command=2 explain the refusal.
Original result/records and scenario PASS/FAIL/ERROR remain unchanged. Explicit prefix
inspection uses shared records readers plus evidence metadata, not ordinary acceptance
projections. A complete journal does not make a truncated report a complete run.

The index retains verdicts and adds an incompleteness diagnostic; HTML displays it
separately from integrity. Intact files and SAVED do not prove completeness. Summary
collections show truncated/unavailable; groups count stored rows, check_accounting
counts all outcomes. DDTT/LCOV retain UNKNOWN without DA, never a misleading zero.

Rebuild derived summary/index/campaign after reader updates: old summaries may be stale.
Pack transports configuration, not a guarantee of future evidence completeness. The PDF
skill renderer consumes prepared evidence; authors must check completeness before
transferring measurements into its input document.

Offline replay: `python tests/renode-backend/replay_consumers.py --runs <campaign>/runs --output <new-directory>`.
Host matrix: test_partial_consumers.py (full/compact, journal/report/both, PASS/FAIL,
unchanged sources and a complete-source positive control).
