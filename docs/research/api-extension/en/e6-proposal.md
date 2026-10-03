# E6: first extension package — proposed decision

[Study](index.md) · [Русский](../ru/e6-proposal.md)

Baseline: commit 1e16415, [API spec 0.1.0](../../../TECHNICAL_SPECIFICATION_API.md),
[E5](e5.md) and [F0/F1](portability.md). Prepared on 2026-10-03.
This is a proposal for approval. Contract 0.1.0 and the core remain unchanged;
permission to continue research is not permission to integrate the prototypes.

## Accepted decisions — 2026-10-03

The owner approved Q1 and Q2 for the first package: deep copies on write/read,
mutable detached results, and ordinary values/dicts without direct Snapshot input
or automatic conversions. These questions are closed. Q5 is partially resolved:
continue/reset within a scenario preserve journal history; a new scenario starts
empty. Context/read freshness remains open. Other provisions below are proposals.
This does not authorize core implementation; specification 0.1.0 continues to
describe current rc.2.

## 1. Scope

Accept only `Target.record` and `Target.records` as the first package. Their value
is accumulating observations, querying and computing statistics within one scenario;
paired comparisons did not reduce line count. A journal should not replace an
ordinary local variable when history is unnecessary.

`read`, context/stack/caller and `finish` remain candidates. F0/F1 strengthened
evidence but did not resolve lifetime, availability, partial stack, ABI, timeout
or cleanup issues. RTOS and first-study hardware debt remain paused.

## 2. Proposed journal contract

| ID | Condition / operation | Proposed behavior |
| --- | --- | --- |
| J1 | `record(name, data) -> None` | Append a detached deep copy after full validation; duplicate names allowed |
| J2 | `records(name=None) -> list[dict]` | Return detached deep copies in insertion order; exact-name filtering; no matches returns `[]` |
| J3 | Entry shape | Exactly sequence/name/data; sequence starts at 1 across the journal and is not renumbered by filtering |
| J4 | Name / filter | Exact built-in nonempty str; None only means no filter |
| J5 | Data | Exact built-ins None/bool/int/finite float/str/list/dict with string keys; reject subclasses, tuple, bytes, GDB objects and cycles |
| J6 | Failed append | No partial entry, logical budget consumption or sequence gap; existing entries unchanged |
| J7 | Ownership | One journal per scenario invocation, initially empty; no sharing across cases, boards or processes |
| J8 | Lifetime | Resume/reset within a scenario retain history; clear keeps its existing breakpoint-cleanup meaning and preserves the journal. Scenario completion releases journal ownership; returned copies remain ordinary Python data |
| J9 | Effects | Python memory only; no GDB calls, MCU reads, continue, file I/O, automatic report export or PASS/FAIL changes |
| J10 | Provenance | Sequence is author insertion order, not an MCU stop number; no automatic PC/time/image/thread/run IDs or atomic hardware-snapshot guarantee |
| J11 | Queries | Python filters/slices/any/all/mean/stdev; no query language. all([]) is true, so the scenario checks nonemptiness |
| J12 | Resources | Owner decision 2026-10-03: externally configurable scenario limits; effective launch configuration is readable by the scenario. General contract pending in Q20 |

J7–J9 require integrated tests: the research facade does not prove future Target
behavior. Export/adapters, the immutable Context model, and a journal-clear operation
are outside this package.

Proposed per-journal defaults (numbers not yet approved): 128 entries, 4096 nodes, 65536 UTF-8 text bytes; data depth at
most 8 (root depth 0), int.bit_length at most 256. Each visited value counts as a
node, including containers, dict keys and entry name. Text includes names, keys
and string values. Wrapper metadata is excluded. Shared references are copied
and counted repeatedly; lone Unicode surrogates are rejected. Logical limits
are not an exact RSS bound: records() copies consume additional caller-held memory.

The owner rejected fixed limits on 2026-10-03. Configuration belongs in the first
package through a general mechanism (Q20), not internal Journal access. The package
now also includes that mechanism.

## 3. Errors and availability

Propose public `RecordError(ValueError)` with machine-readable `code`:
invalid_name, unsupported_type, invalid_text, non_finite, cycle, limit_exceeded.
The last carries `limit`: records, nodes, depth, text_bytes or integer_bits.
Message text is not a code. Multiple invalid conditions guarantee rejection without
append, not a specific diagnostic priority. This is **new work**, not the already
tested E1 contract.

Invalid records filters also produce invalid_name. Environmental exceptions,
including MemoryError, are not disguised as data-validation failures. Unhandled
exceptions produce system ERROR; check mismatches produce FAIL. Propose exporting
RecordError from stm32_gdbtest for explicit handling in the future integration.

Check both callable operations before the new scenario's first action. Absence
produces an explicit ERROR requiring the supporting version, with no silent skip
or fallback. API_VERSION currently does not serve as a method registry.

## 4. Revisions and versions — proposal

| Quantity | Proposal |
| --- | --- |
| API spec 0.1.0 | Preserved baseline describing current rc.2 |
| Document PATCH: 0.1.1 | Clarification/correction without changing compatible behavior; new board measurements alone do not require a revision |
| Document MINOR: 0.2.0 | Accepted compatible operations such as record/records |
| Incompatibility | Separate decision and migration; MAJOR after 1.0, MINOR explicitly labelled breaking before 1.0; never hide in PATCH |
| Package | Existing VERSIONING policy points to 0.2.0; select the exact prerelease when preparing release |
| API_VERSION | Propose keeping 1 for additive compatibility; existing operations/case convention unchanged. Redefining this number needs a separate decision |
| JSON/TOML schemas | No change for a runtime journal that is not exported |

Document and package versions remain independent even if both become 0.2.0.
Approve the contract first, then authorize implementation separately. The new
revision describes accepted requirements; implementation/verification status is
tracked separately. A version increment is neither a release nor hardware acceptance.


Q1–Q20 statuses and accepted decisions are maintained in the [plan register](plan.md).
Recommendations in this document do not close questions by themselves.

## 5. Q1–Q16 disposition

The table preserves E6 recommendations; acceptance of Q1/Q2 and part of Q5 is
recorded above. The plan register owns current statuses and decision scope.

| Question | Proposed decision / route |
| --- | --- |
| Q1 | Detached mutable deep copies J1/J2; do not call them immutable Context |
| Q2 | Defer Snapshot adapters; explicitly build dicts of supported values |
| Q3 | Journal uses J7/J10 only; common read/context provenance is a later package |
| Q4 | RecordError.code for the journal; read/stack availability separately |
| Q5 | Journal history is not invalidated; context freshness needs separate work |
| Q6 | Accept observation value without promising fewer lines; measure boundary memory/time before integrated acceptance |
| Q7 | Journal needs no GDB Python capabilities; question remains for other methods |
| Q8 | Prefer unconfirmed_end for NO_REASON; decision/tests belong to a future stack package |
| Q9–Q12 | Keep finish experimental; timeout, ABI, slots/locations and negative hardware cases remain debt |
| Q13 | Journal adds no GDB handlers; primary-error/cleanup policy remains a separate task |
| Q14–Q15 | Resolve Mapping/freshness and explicit unknown caller before accepting context/stack |
| Q16 | First package J1–J12 plus errors above; versions per section 4; owner decision required |

## 6. Acceptance after implementation authorization

A1–A6 are local proposal identifiers, not approved specification test cases.

| Check | Criterion |
| --- | --- |
| A1: contract transfer | New API requirement/TC IDs, J → requirement → test mapping; old eight operations unchanged |
| A2: journal | Order, duplicates, nested copies, all limit boundaries; rejection preserves entries/sequence/budget |
| A3: integration | Real Target: isolated invocations, clear/resume preserve history, original exceptions retained, no unsolicited report export |
| A4: diagnostics | Each code/limit, early refusal on old API; exceptions do not become FAIL or empty results |
| A5: resources | Measure maximum-journal fill/repeated reads on the GDB host; retain time/memory and discuss acceptability before acceptance; no numeric requirement yet |
| A6: compatibility/HW | Core host regression and paired old/new ADC/measurement scenarios on F0/F1/F411; preserve checks/outcomes, compare semantics rather than identical temperatures between runs; baseline/restore required |

E1–E4 support this plan but do not close A1–A6 for integrated code. After approval,
write normative requirements and their matrix; after separate integration permission,
implement and run acceptance.

## 7. Questions appended to the queue

- Q17 closed 2026-10-03: configurable scenario parameters and readable launch
  configuration approved. The previous fixed-limit recommendation is superseded.
- Q18: approve RecordError.code/limit and public exception import.
- Q19: set acceptable memory/time costs from A5 measurements; logical limits are
  not measured RSS/latency guarantees.

## Q20: proposed configuration shape

Direction approved; the following is proposed, not implemented API:

```python
limit = t.config["limits"]["journal"]["max_records"]
threshold = t.config["parameters"]["vdda_min_mv"]
```

1. t.config is a deeply immutable snapshot of effective parameters for this run,
   including defaults, rather than the source TOML.
2. Proposed precedence: API defaults → scenario parameters → external overrides
   for the selected scenario ID. File/CLI syntax is undecided.
3. limits contains typed API constraints; parameters contains consumer values such
   as measurement thresholds. Validation/types need a contract. Unknown API keys
   and invalid types are rejected before hardware connection.
4. Configuration is frozen before execution and survives resume/reset unchanged.
   It is separate from dynamic MCU context and mutable internal profile data.
5. Do not automatically expose the entire stand/session, environment or connection
   data. A schema defines public parameters.
6. The system spec owns loading/merging/transport; the API spec owns read access and
   limit use. Reproduction metadata and possible report-schema changes require
   explicit decisions before implementation.

Q6/Q19 remain open: configurable limits strengthen the need for measurements.
Extend A2/A3/A5 with defaults/overrides, scenario isolation, nested config mutation
rejection and invalid configuration refusal before connection.
