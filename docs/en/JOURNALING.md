# Journaling

[Documentation](index.md) · [API](API.md) · [Results](RESULTS.md) · [Русский](../ru/JOURNALING.md)

## Availability

This guide describes the 0.6.0 candidate branch, not everything shipped in 0.5.0.
A2 and A3.1 are implemented. A3.2 currently supports configuration validation and
transport only: inspect/prepare/pack accept API schema 3. Execution rejects it with
api_execution_unsupported before probe ownership/server startup, even with on_limit=error.
Use schema 1/2 for execution until storage policies are implemented. No truncation occurs.

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
| pack / open | Snapshot transport; opening does not admit schema 3 execution |
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

## Planned truncation

The next package will preserve a prefix and stop storing details in the affected store,
while checks and cleanup continue. Command code 2 remains. Invalid input, transport,
storage and recovery errors will not be suppressed. Explicit partial records reading
is planned, not implemented. Do not execute schema 3 until that package is accepted.

Inspect configuration offline, select budgets, enable capture, then assess scenario,
command, capture, evidence and cleanup separately before evaluating DDTT applicability.
Examples: tests/renode-backend/run_report.py; host tests: test_evidence.py and
 test_policy_config.py. An intentional ERROR checks the tool contract, not MCU behavior.
