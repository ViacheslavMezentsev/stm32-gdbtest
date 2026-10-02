# API evolution: proposed conventions and specification process

[Documentation](index.md) · [Русский](../ru/api-evolution.md)

2026-10-02. **Proposal for agreement**, not a new normative specification revision.
The current R1–R18 research cycle is concluded with [technical debt](technical-debt.md).
Next comes discussion of conventions and a small extension; HW remains paused.
Candidates are in [api-proposal](api-proposal.md). This document proposes how to
accept and verify changes; it does not approve those candidates.

## 1. Document responsibilities

Recommendation: a subordinate Target API specification with independent revisions
and one owner per requirement, rather than two competing specifications.

| Document | Responsibility |
| --- | --- |
| [System specification](../../../TECHNICAL_SPECIFICATION.md) | System: host/agent lifecycle, backend, stand, process timeout, PASS/FAIL/ERROR reports, CMake/CLI, integration and system acceptance |
| Future `docs/TECHNICAL_SPECIFICATION_API.md` | Target API subsystem: public operations/data models, preconditions/postconditions, errors, resources, compatibility and contract verification |
| Future `docs/ru/API_EVOLUTION.md` and EN counterpart | Practical conventions and change process; reference normative requirements instead of duplicating them |
| [Current API guide](../../../en/API.md) and RU counterpart | Implemented/released operations, examples and migration |
| Research and API proposal | Evidence, alternatives and limitations; not approved contracts |

Future filenames are proposals; those documents do not exist yet. Conventions are
discussed here for now. Maintain both specifications in Russian only using
[embedded-tech-spec](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/embedded-tech-spec),
as required by [maintenance](../../../en/maintenance.md). Revisions are independent;
document revision, API_VERSION, data schema and package version are different values.

The system specification already has §5.10. Do not copy it wholesale: boot/import/
scenario outcome are system responsibilities; public contracts belong to API.
Prepare an “old clause → owning document → new clause/reference” transfer table.
Retain old numbers as delegating references or explicitly excluded clauses with
history, never reuse them. System requirements reference API contracts; API
requirements reference system constraints. Every disputed clause has one owner.

Qualify code/test references by document, for example `ТЗ API <clause>` /
`ТЗ проекта <clause>`; TC-01 in different documents is not the same test case.
Cross-document matrices use `(document, clause/TC, revision)`, not bare numbers.
Current check_spec support for these links is unproven: CI currently checks only
the system specification. Before accepting a second specification add strict
checks for both documents and cross-reference/coverage validation.

## 2. Proposed conventions

| ID | Rule for agreement | Verification |
| --- | --- | --- |
| E1 | One primitive, one action; distinguish reading, continuation and intervention in contracts | Every method lists effects and forbidden implicit actions |
| E2 | Python snake_case; optional policies/limits keyword-only; units in names, e.g. timeout_s | Check public signatures, types, units, ranges and defaults |
| E3 | Old scenarios preserve behavior on newer versions in previously supported configurations; no silent type/error/default changes | Existing API regression and additive/behavioral/breaking change matrix |
| E4 | New features are not declared available on old versions; deprecation and removal are separate | Explicit unavailability, migration plan and agreed removal interval; never invent an interval automatically |
| E5 | Typed, materialized results with provenance/availability; snapshots are not live handles | Serialization, immutability, bounds, lifetime and unavailable-value checks |
| E6 | Invalid inputs, unsupported configuration and expectation mismatch are distinct cases | Outcome table, error types and mapping to system FAIL/ERROR |
| E7 | No hidden resume, software fallback, first-location selection or retry after call | Negative checks and observation of actual events/effects |
| E8 | Every resource has owner, bound and cleanup order; every wait is case-budget bounded | Exhaustion, foreign resources, interruption and cleanup failure; preserve primary error |
| E9 | Main-thread GDB API only; snapshots and frame references have different lifetimes | Host invalidation model plus GDB integration checks; MCU contract separately |
| E10 | Support depends on operation/build/ABI/MCU/backend/GDB, not one version | Separate mechanism available, verified, known failure and untested statuses with evidence links |
| E11 | Every new contract gets clauses, positive/negative TCs and traceability before implementation | No normative requirement without A/T/I/D method and acceptance criterion |
| E12 | Agree contracts first, authorize implementation separately; old prototype evidence does not automatically accept new code | Implementation/final checks tied to commit and declared configurations |

Do not silently override [version policy](../../../en/VERSIONING.md). It currently
assigns pre-1.0 new features to 0.2.0, whereas research was named rc3. Before choosing
a release target, explicitly decide whether to clarify the policy for candidates
of unreleased 0.1.0 or target the extension at 0.2.0. Research naming does not
authorize changing that rule. API_VERSION need not equal package version or either
specification revision.

## 3. Operation contract card

Before implementation complete one card: purpose/exclusions; signature/types/
defaults/units; permissible MCU/GDB state; input constraints; successful result;
alternative outcomes; effects and invalidated objects; ownership/cleanup; time/
memory/slots; compatibility; specification clauses and TCs. Describe shared models
(Context, StackSnapshot, FrameRef, StopResult) once and reference them from operations.
Do not start with a large method list.

| Case | Expected operation behavior | Scenario/check assessment |
| --- | --- | --- |
| Valid input, supported configuration | Specified result, exact stop reason and only declared effects | PASS after independent result verification, not merely no exception |
| Invalid type/range/stale reference | Specified diagnostic error before intervention where possible | Negative host test passes by verifying rejection/no unwanted effects; unhandled scenario error remains ERROR |
| optimized_out/out_of_scope/unreadable value | Specified availability or error, never substitute zero | Verify expected status; unavailability is not a successful value |
| Partial stack/unexpected stop | Explicit incompleteness/interrupted, not false target arrival/caller absence | According to agreed result contract and scenario expectation |
| Actual value differs from expected | Correctly obtained result; check records mismatch | FAIL, not infrastructure ERROR |
| Fault/connection loss/external timeout | ERROR diagnostics; possibly partial report, method return not guaranteed | Fault/recovery check separate from original ERROR; never rewrite its status |
| Cleanup fails after primary error | Preserve both causes and actual restored/unrestored resources | No PASS merely because primary error was expected |

Small-change example: start with `frames`/StackSnapshot and caller helpers. Not yet
selected release scope, but effects are limited and R1/R2/R6/R15 provide foundations.
Initial TCs: order/exact depth; nearest ancestor; stack end; depth_limit/unwind_error;
unavailable name; recursive/inline; immutability; stale FrameRef; no selected-frame
change or implicit continue. Use independent expected values and negative controls,
not tests mirroring implementation. Host PASS cannot replace GDB/HW evidence.

## 4. Transition order

1. Conclude the current research cycle, retaining reports and open debt.
2. Agree E1–E12, document boundaries and version policy; record decisions explicitly.
3. Prepare API specification from the skill template: initial revision 1.0 “draft
   for agreement”; separate existing API baseline from extensions/open questions.
   Structure: scope, models/lifecycle, operations, errors, interfaces, nonfunctional
   limits, evolution, verification, matrix, questions and appendices.
4. In the agreed transition update the system specification to its next revision
   (currently 0.58): API delegation, cross-document links, conventions and system
   acceptance. Reconcile both documents and CI in one change set, without two truths.
5. Select one small extension, complete its contract cards/TCs and approve its contract.
6. After separate authorization implement and run host/GDB checks; required hardware
   acceptance follows only after separate HW resumption. Until then do not claim
   unverified hardware guarantees as supported.

Current result: concluded research cycle and these draft conventions. Next discussion:
**the two specifications' boundaries, E1–E12 and version choice**. Normative documents
are not rewritten now: alternatives remain under discussion and current §5.10 is
still the source of the existing contract.
