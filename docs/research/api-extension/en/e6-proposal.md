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

Error model approved by the owner on 2026-10-03 (Q18 closed): public
`RecordError` with machine-readable `code`. Proposed base class remains ValueError,
as in the research prototype. Approved codes:
invalid_name, unsupported_type, invalid_text, non_finite, cycle, limit_exceeded.
The last carries `limit`: records, nodes, depth, text_bytes or integer_bits.
Message text is not a code. Multiple invalid conditions guarantee rejection without
append, not a specific diagnostic priority. This is **new work**, not the already
tested E1 contract.

Invalid records filters also produce invalid_name. Environmental exceptions,
including MemoryError, are not disguised as data-validation failures. Unhandled
exceptions produce system ERROR; check mismatches produce FAIL. Public RecordError import enables explicit handling in future integration; core remains unchanged.

Check both callable operations before the new scenario's first action. Absence
produces an explicit ERROR requiring the supporting version, with no silent skip
or fallback. API_VERSION currently does not serve as a method registry.


Also approved: rejection consumes no budget and adds no partial entry; system
errors including MemoryError are not converted to RecordError. Scenarios can
catch and inspect code/limit without parsing message text.

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
- Q18 closed 2026-10-03: public RecordError.code/limit model approved.
  Codes and negative regression still need implementation; old E1 does not prove them.
- Q19: set acceptable memory/time costs from A5 measurements; logical limits are
  not measured RSS/latency guarantees.

## Q20: session.toml and linked files

Approved by the owner on 2026-10-03: external session.toml links configurations
for the scenario session. api.toml separately describes API settings/features;
the combined scenario.toml proposal is superseded. The scenario can read its
launch configuration; the concrete read interface remains under discussion.

```toml
# session.toml
[config]
api = "api.toml"
target = "target.toml"
image = "full_image.toml"
```

This expresses the approved config.api/config.target/config.image links in TOML.

| File | Responsibility | Status |
| --- | --- | --- |
| session.toml | Select linked session configuration files | Approved, not implemented |
| api.toml | API settings used in the session, including journal limits | Separation approved; content schema open |
| target.toml | MCU and hardware profile constraints | Existing schema 1 |
| full_image.toml | Image region, fill and CRC policy | Existing [image] schema, selected filename |

Links select names; existing full-image.toml files are not renamed. Inspected at
470d90c: profile.load_profile strictly validates target; full_image.load_policy
reads [image], validates against target and returns the table plus file SHA256.
Runner passes profile/full_image_policy to the agent via run.json; Target receives
only the internal mutable profile. No general public configuration read API exists.

Existing session.json is a generated internal launch artifact accepted by --session.
New session.toml is the proposed user-authored configuration entry point; it does
not automatically replace JSON. TOML loading, CMake/CLI/JSON integration and legacy
launch compatibility require a contract.

Approved by the owner on 2026-10-03: t.config contains effective configuration,
validated known parameters and added defaults. Explicit values are not overwritten;
unknown fields are retained. Keys match config.* names and nesting preserves TOML:

```python
mcu = t.config["target"]["mcu"]
image_end = t.config["image"]["image"]["end"]
limit = t.config["api"]["records"]["max_records"]
```

Repeated image denotes the selected document and its existing [image] table.

t.config_props is the approved name for source configuration properties:

```python
props = t.config_props["api"]
if props is not None:
    original = props["data"]
    digest = props["sha256"]
    reference = props["reference"]
```

data is parsed TOML without added defaults, comments or formatting; sha256 hashes
original bytes; reference is the link from session.toml, not a guarantee that this
path exists on a remote stand. Both views are deeply immutable and derived from
a single read of each selected file during preparation. Without config.api,
config_props["api"] is None while config["api"] contains defaults. Without
config.image both corresponding values are None. An invalid referenced file is
still an error, not absence. The name config_sources is not used.

Items 1–3 approved by the owner on 2026-10-03; items 4–5 remain proposals:

1. Resolve relative config.* paths against session.toml, not cwd; no implicit
   search for same-named files in neighboring directories.
2. Load/validate selected files before MCU connection; expose immutable content
   snapshots rather than reopening paths in GDB. Source edits after preparation
   do not change the current run; remote hosts need no original user-host paths.
3. config.target is required. config.api is optional: an absent reference selects
   documented API defaults. config.image is optional: absence retains ELF load-section
   verification. An explicitly referenced missing or invalid file gives ERROR before
   MCU connection; no substitute file or defaults replace an erroneous file.
   Numeric defaults remain undecided; omitted known fields using defaults are approved.
4. Decide where script-specific parameters belong; separate api.toml does not
   automatically place board thresholds/expectations there.
5. data/sha256/reference metadata and source/effective distinction are approved
   above. Stand configuration access and reproduction storage remain undecided.

Q20 remains open with file roles/links accepted. Decorator/override precedence is
not approved. The system spec owns loading/validation/transport; the API spec owns
public reads and limits. Core and API spec 0.1.0 remain unchanged. Q6/Q19 stay open.
Acceptance covers selected versus adjacent files, absent references versus broken
paths, edits after capture, remote execution, nested mutation refusal and validation
before connection.

### Next proposal: api.toml contents

Approved by the owner on 2026-10-03: `[records]` is shared by `record()` /
`records()`. Section names follow public methods or related method groups, not
internal implementation names such as Journal. Loading rules below are approved;
numbers remain proposals from the research prototype:

```toml
schema = 1

[records]
max_records = 128
max_nodes = 4096
max_text_bytes = 65536
max_depth = 8
max_integer_bits = 256
```

Approved by the owner on 2026-10-03: schema is required when the file exists;
records and individual known fields may be omitted in favor of documented defaults.
Experimentally accept unknown api.toml fields and sections and retain them in the
scenario-readable snapshot, including unknown fields inside known sections.
The API neither interprets them nor strips them during validation. Known parameters
are checked for type/range; invalid values produce ERROR before connection rather
than replacement with defaults. Invalid TOML is still rejected. This decision does
not automatically change existing target.toml or full_image.toml schemas.

Proposed constraints: limits are positive integers excluding bool; supported schema
is integer 1. Upper bounds require Q6/Q19 evaluation; arbitrary sizes are not declared
verified. File schema is distinct from API specification revision and API_VERSION.
Scenarios may read consumer data from API-unknown sections; consumers validate their
application semantics. A dedicated namespace and future API-name collision rules
remain open in Q20. Full-content transport (including TOML types not directly
representable in JSON) needs a contract; source/defaults access is approved as
config_props/config. Silent field loss is unacceptable. Accepting structure does
not approve numeric defaults.

Acceptance additions: unknown sections/nested keys remain readable; known fields
with invalid type/range are rejected even alongside unknown keys; missing known
fields receive defaults. Retained consumer fields follow snapshot immutability.
For config_props also verify hashes against original bytes, no defaults in data,
defaults in config, None for omitted files and nested immutability of both views.
These are future acceptance checks, not results from an implemented API.

### How session.json is currently produced

stm32_gdbtest_attach in STM32GDBTest.cmake uses file(GENERATE) during CMake
generation to write build/<configuration>/hwtest/session.json. Fields: elf, gdb,
tests, root, out, stand, profile, build_manifest. These reference artifacts and
directories, not target.toml contents or test results. stand may be empty and
selected at launch. ELF and build-manifest are produced by building; the manifest
is POST_BUILD, not generated together with session.json. CLI reads JSON, selects
the --test case and invokes runner, which loads configurations and writes a separate
run.json for the GDB agent. Results are separate. Image policy currently comes from
--image-policy or the environment, not those eight CMake-generated fields. This is
an internal format without a stable user-schema promise; generated files are not
normally edited manually.

[Q20: session.toml migration plan](session-migration.md) — CMake/CLI, shared snapshots, conflicts, compatibility and M1–M6 checks. Proposal only, not core integration approval.

### Approved: TOML transport and defaults compatibility — 2026-10-03

Owner decision: transfer original selected TOML bytes as base64 in internal JSON
with SHA256. The receiver verifies hashes and parses transferred bytes without
opening original paths. TOML types and unknown fields survive; scenarios see
ordinary immutable config/config_props, not base64 API values.

Preparation and execution defaults must match. Mismatch produces ERROR before
connection, with no automatic receiver-default substitution. Use a compatible
tool version or prepare the package again. M4 tested a defaults fingerprint;
the envelope algorithm/version will be fixed during integration. Matching defaults
alone does not prove compatibility of all other versioned contracts.

This part of Q20 is approved; legacy config_props, bounds/name collisions and
integration details remain. Normative API 0.1.0 and core are unchanged.

### Approved: legacy-mode config/config_props — 2026-10-03

Owner decision: launches without session.toml retain existing selection rules,
while the new read interface uses the same shape:

| Section | config | config_props |
| --- | --- | --- |
| target | Actual profile loaded via session.json | data/sha256/reference of the selected file |
| api | Default API settings | None: no API file selected |
| image | Actual CLI/environment-selected policy or None | data/sha256/reference of the selected file or None |

Legacy-package properties describe the packaged file, not an invented original-host
path. No session.toml is fabricated. Immutability, byte/hash consistency and the
source/defaults distinction remain identical. Old scenarios need not use new properties.

This is an accepted requirement, not completed integration. Prior legacy regressions
do not prove these properties exist in production Target. Test the adapter separately
before new-core acceptance. Q20 remains open for integration details and future name
collisions; numeric bounds belong to Q6/Q19.

### Approved: parameter names and schema evolution — 2026-10-03

schema determines known api.toml parameters and their meaning. A newer tool must
not reinterpret unknown fields under an older schema. Recognizing a new parameter
requires a new schema version and explicit migration; old files retain their meaning
within a supported old schema.

[user], for example [user.measurement], is recommended for consumer data and is
not interpreted by the API. This is a convention, not a ban on other unknown fields
or sections: they remain retained and readable. A new schema version does not
automatically approve package/API_VERSION/API-spec changes.

Q20 is closed within the agreed first-package scope: files, references, defaults/
validation, read-only interfaces, transport, legacy mode and naming rules are defined.
Implementation/acceptance remain M5/M6 work; closing a question does not complete
them. Numeric bounds/costs remain Q6/Q19, versions/final scope Q16. Additional stand
information is not included automatically. Earlier unresolved-Q20 lists above are
discussion history; the plan register owns current status.
