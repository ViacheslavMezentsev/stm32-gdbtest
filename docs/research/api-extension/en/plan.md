# Research plan

[Research](index.md) · [Русский](../ru/plan.md)

## Baseline and boundaries

The compatibility baseline is v0.1.0-rc.2, commit
`a0d6547ba83b7c911f8f3028cb064aeedd3e5a36`.
The working tree baseline is recorded in the [research index](index.md).
Original scenarios remain available for comparison; signatures below are provisional.
Prototypes will live separately in `tests/api-extension` once implementation starts;
they must not replace Target, the runner or the installed package.

## Candidates and intended benefit

| Stage | Candidate | Existing scenario and intended benefit |
| --- | --- | --- |
| E1 | `record(name, data)` | [ADC](../../../../tests/firmware/profiles/f411ce/tests/board/test_adc.py), [HAL runtime](../../../../tests/hal-f030/hal_scenarios/peripheral_runtime.py): replace direct report writes with an evidence contract |
| E2 | Bounded typed `read` | Same scenarios: read arrays and selected fields without repeated value calls; define size and depth limits |
| E3 | `frames` and minimal `context` | [Sleep/WFI](../../../../tests/firmware/profiles/f411ce/tests/board/test_sleep.py): remove direct GDB frame traversal while preserving interrupted-context recognition |
| E4 | `finish` | [HAL methods](../../../../tests/hal-f030/profile/tests/board/test_hal_methods.py): check effects immediately after a natural return |
| E5 | API conventions and properties review | Compare each developed method's contract and evidence with the three source documents; list matches and gaps |
| E6 | API acceptance and scenario migration | Following a positive E5 decision, agree on versioning and open questions, accept the API and revise current scenarios |

For each stage: describe its experimental contract and negative cases, implement an
isolated prototype and compare scenarios, then produce a separate report.
Snapshots and events must be materialized, serializable and bounded in size;
results must not contain live GDB objects. All GDB calls run on its main thread.

- E1: define duplicate names, entry ordering, invalid values and size limits;
  recording errors must not hide the original FAIL/ERROR.
- E2: missing symbols, optimized-out values, memory errors, arrays/structures,
  field selection and limits; prohibit implicit function calls. Reads do not
  promise atomicity with running DMA. Existing integer value semantics remain unchanged.
- E3: stack end, depth limit, unwind error, unnamed and signal frames, snapshot
  freshness after resuming. An incomplete stack does not establish caller absence.
  Caller search and interrupted-frame selection remain techniques.
- E4: normal return, void/scalar, unavailable value, another breakpoint, fault,
  timeout, hardware breakpoint exhaustion and cleanup. Do not promise unverified
  ABIs/aggregates. Preserve fault guards and external timeout/recovery.

## Comparison and criteria

1. Preserve original and experimental variants, map every assertion and retain
   independent expected values. Fewer assertions are not an improvement.
2. Compare scaffolding lines, direct GDB/report accesses, diagnostic data and
   negative outcomes. Count prototype lines separately from scenario lines.
3. Check contracts with controlled host failures; these tests do not establish
   actual unwind, ABI, breakpoint or MMIO behavior.
4. After resuming hardware work, compare variants on the same ELF and settings.
   Start with F411, then check F030/F103/F401 portability; F429 when a bench is available.
   Record MCU, GDB, backend, optimization, ABI, ELF/manifest hashes and halt/reset effects.
5. For finish, account for the changed observation point: HAL return and a later
   application checkpoint establish different properties. Keep both if removing
   either weakens the scenario.

Each stage receives a separate RU/EN `eN.md` report; sanitized JSON goes in
`results/`, linked from its report and registry. Preserve original FAIL/ERROR
outcomes instead of replacing them with successful retries. Do not commit raw
logs, ELF files or local TOML configurations.

## Closing stages

### E5: conformance review before acceptance

Sources: [api-evolution.md](../../rc3-gdb-python/en/api-evolution.md),
[api-proposal.md](../../rc3-gdb-python/en/api-proposal.md),
[execution-context.md](../../rc3-gdb-python/en/execution-context.md).
This stage follows E1–E4; stage IDs E1–E6 are distinct from convention IDs E1–E12
in api-evolution.md.

For every method and data model, prepare this checklist:

- Simplicity and unambiguous purpose; separation of reading, resuming and intervention.
- Names, types, units, parameterization, keyword-only policies and limits, defaults.
- Compatibility with rc.2: existing scenarios, types, errors and behavior;
  additive/behavioral/breaking classification and missing capability detection.
- Materialization, typing, provenance and availability; no live GDB objects,
  immutable snapshots or explicitly agreed copy semantics.
- Lifetime, run/stop/revision and invalidation after resume, writes, reset/reconnect;
  snapshot versus frame reference and MCU state consistency boundaries.
- Distinct invalid inputs, unsupported cases, FAIL and ERROR; incomplete stacks
  and unavailable values without fabricated success or zero substitution.
- No hidden resume/call/retry/fallback; GDB main thread and explicit MMIO effects.
- Resource ownership, memory/breakpoint limits, time budgets, cleanup and primary
  error preservation; exhaustion and interrupted operations.
- API/technique/pattern boundaries; support by operation/ABI/MCU/backend/GDB,
  separate verified/untested/known failure states and supporting reports.
- Testability, negative cases, migration, documentation and requirements traceability.

For each item in `e5.md`, record the method, a specific source-document reference,
evidence and status: conforms / partial / differs / untested / not applicable
(with reason). Intent is not evidence. List gaps, proposed corrections and owner
questions separately. One known E1 question: whether detached mutable records copies
are sufficient for a journal when execution contexts require deeply immutable
snapshots; do not automatically equate these different contracts. Review provenance too.

### E6: acceptance and adoption

Entry requires reviewed E5 results and explicit owner agreement on API scope,
accepted limitations and remaining debt. This plan does not constitute acceptance.

1. Resolve open questions from the original proposal and E5; agree on final
   signatures, data models and errors.
2. Agree on API version format and rules, its relationship to API_VERSION, package
   version, data schemas and specification revisions; define compatibility and release target.
3. Record accepted conventions and a separate API specification with cross-references
   to the system specification, without duplicating requirements; define migration
   and acceptance criteria.
4. After core integration approval, implement the accepted scope and revise current
   scenarios while preserving checks and expected outcomes; update API RU/EN,
   CHANGELOG and normative documents under project rules.
5. Run legacy-call regression and revised-scenario acceptance on agreed configurations;
   preserve comparisons and limitations in `e6.md`. Publication and release remain
   a separate owner step.

## Deferred tools

Watchpoints, GDB function calls, arbitrary PC writes, universal MMIO rollback,
RTOS and advanced assembly operations are outside E1–E4. Counter arithmetic,
ranges and MCU-specific expectations remain consumer techniques.
The study produces an API scope recommendation and limitations, followed by separate
approval of conventions/API specification and core integration; no release target is implied.

## Questions and proposals for review after the stages

This register owns Q1–Q20 statuses; E6 contains proposals, not decisions.
Closed requires an explicit owner decision recorded with its date. Closing a
question does not imply implementation or acceptance. Deferred questions remain
Open; composite questions retain partial decisions but stay Open until every part
is resolved. IDs are stable. As of 2026-10-03 Q1, Q2 and Q17 are closed for the first package; Q5 and Q16 are partly resolved.
Other questions remain open. Contract decisions do not authorize core integration.

| ID | Source | Question / proposal | Review | Status | Decision / basis |
| --- | --- | --- | --- | --- | --- |
| Q1 | E1 | Keep records as detached mutable copies or unify with deeply immutable snapshots? | E5 | Closed | Owner decision 2026-10-03 for the first package: detached deep copies on write/read; returned copies are mutable and their modification does not change the journal. |
| Q2 | E1/E2 | How to extract Snapshot data and pass it to record conveniently without losing types? Direct Snapshot recording is currently rejected; automatic export is out of scope. | E5 | Closed | Owner decision 2026-10-03 for the first package: authors explicitly supply ordinary values/dicts; direct Snapshot input and automatic conversions excluded. Future adapters require a separate proposal. |
| Q3 | E2/E3 | Shared provenance model: actual run/image ID, inferior/thread/core, stop/revision; associate read with context capture time. | E3/E5 | Open | Not approved; recommendation in E6. |
| Q4 | E2/E3 | Refine availability/errors: missing fields, optimized-out, unreadable and partial stacks; keep distinct from assertion FAIL. | E5 | Open | Not approved; recommendation in E6. |
| Q5 | E3 | Which operations automatically invalidate snapshots? Raw monitor/reset/reconnect and thread/core switches need policy; current explicit invalidate is incomplete. | E5 | Open | Partial owner decision 2026-10-03: the journal retains history across continue/reset within a scenario; a new scenario starts empty. Context/read freshness rules remain unresolved. |
| Q6 | E1/E2 | Is the benefit sufficient without fewer lines? Measure copying memory/time, define limits and convenient access; avoid replacing locals with journals unnecessarily. | E5 | Open | Not approved; recommendation in E6. |
| Q7 | E3 | Probe required capabilities of the installed GDB instead of inferring support from version: the tested build lacks FIRST_ERROR. | E5 | Open | Not approved; recommendation in E6. |
| Q8 | E3 | Classify older=None + NO_REASON separately as unconfirmed_end? Current unwind_error retains reason but does not imply corruption; agree on tri-state caller and exact signal/inline depth counting. | E5 | Open | Not approved; recommendation in E6. |
| Q9 | E4 | Separate timeout_s or only a case budget? General finish requires HW timeout/recovery and distinct fault/exit outcomes; host doubles are insufficient. | E5 | Open | Not approved; recommendation in E6. |
| Q10 | E4 | Explicit hardware point plus ABI read, or gdb.FinishBreakpoint? Compare result capture and resources; scalar PASS does not establish wider types. | E5 | Open | Not approved; recommendation in E6. |
| Q11 | E4 | How to represent locations, foreign/coincident points and cleanup errors? Currently uses conservative object counts and cleanup_errors list. | E5 | Open | Not approved; recommendation in E6. |
| Q12 | E4 | Which configurations and negative HW cases are mandatory before finish acceptance? HAL F030, signed/other ABIs and invalidation integration remain unverified in E4. | E5/E6 | Open | Not approved; recommendation in E6. |
| Q13 | E5 | How to retain primary and all disconnect/cleanup failures in a common result? C.close can mask a primary error; F keeps cleanup errors in its backend. | E6 | Open | Not approved; recommendation in E6. |
| Q14 | E5 | Approve Mapping with frames/state_revision/stop/meta/availability or explicitly narrow the draft? current must account for selected thread/inferior/image; currently it can falsely report freshness. | E6 | Open | Not approved; recommendation in E6. |
| Q15 | E5 | Keep caller_is → bool/None or use a named result that cannot implicitly become False? Incomplete stacks need an explicit decision. | E6 | Open | Not approved; recommendation in E6. |
| Q16 | E5 | Accept record/records first and defer finish? Agree on initial scope, SemVer/release target (current policy: 0.2.0), and API_VERSION format/rules independently of schemas/specifications. | E6 | Open | Partial: on 2026-10-03 the owner approved a separate API spec, X.Y.Z and baseline 0.1.0. Extension scope, increment rules, package version and API_VERSION remain unresolved. |

[E1–E4 continuation on F0/F1](portability.md): 8/8 HW per board, limitations and retained prepare ERROR. [API spec 0.1.0](../../../TECHNICAL_SPECIFICATION_API.md) captures current rc.2 without integrating extensions. Next: Q1–Q16 review and E6 approval.

[E6: proposed first package](e6-proposal.md) — record/records contracts, Q1–Q16 recommendations, versions and acceptance. New Q17–Q19 are appended to the queue; core integration is not approved.

| ID | Source | Question / proposal | Review | Status | Decision / basis |
| --- | --- | --- | --- | --- | --- |
| Q17 | E6 | Fixed or configurable first-package limits? | E6 | Closed | Owner decision 2026-10-03: limits are scenario parameters with external configuration; the scenario can read its launch configuration. General mechanism contract: Q20. |
| Q18 | E6 | Approve RecordError.code/limit and public exception import. | E6 | Open | Not approved; recommendation in E6. |
| Q19 | E6 | Set acceptable memory/time from A5; logical limits do not guarantee RSS/latency. | Acceptance | Open | Not approved; recommendation in E6. |
| Q20 | Q17 decision | General scenario configuration: schema, sources/precedence, validation, read-only access, exposed data boundaries and reproducibility. | Before first-package implementation | Open |Partly approved by owner 2026-10-03: session.toml with config.api/target/image and separate api.toml. Also approved: paths relative to session.toml and immutable content snapshots for scenarios including remote execution. Also approved: target required; api/image optional with API defaults/ELF-section verification; invalid referenced files give ERROR before connection. Read interface, api schema and script parameters remain open; see E6. |
