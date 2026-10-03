# 0.3.0 plan: scenario API audit and redesign

[Documentation](index.md) · [Русский](../ru/API030_PLAN.md)

Owner decision, 2026-10-04: audit the API and design a new operation set for **0.3.0**.
The direction and names below are agreed for design. Signatures, result models, errors,
support boundaries and migration still require agreement. This is a plan, not the current reference.

The current candidate remains 0.2.0rc1; this document does not change the
[current API](api/index.md) or [API specification](../TECHNICAL_SPECIFICATION_API.md).
The 0.3.0 target does not automatically assign API_VERSION, specification revision,
schema numbers or a prerelease tag. Implementation and publication are separate later stages.

## Target surface for design

Parentheses indicate operations, not final signatures. settings and sources are properties.

| Existing API | Possible development | Recommendation |
| --- | --- | --- |
| check(name, actual, expected) | Validated check with detached data snapshot | Keep name and purpose; agree types, errors, bounds and report integrity |
| value(expression) | read(path, ...) and evaluate(expression, ...) | Replace after design; separate object reading from C/C++ expression evaluation |
| set_value(expression, value) | write(path, value, ...) | Replace; define objects, partial effects and readback policy |
| fields(expression, expected) | read(..., fields=...) plus table-check technique | Consider moving to a technique; remove only after covering all former uses |
| breakpoint(...) | breakpoint(...) returning a managed point | Keep name; redesign ownership, with/remove, arguments and cleanup |
| reach(function, when) | reach(location, ...) returning an operation result | Keep name but change contract: navigation returns outcomes, assertions are explicit |
| force_return(expression) | ret(value, *, frame=...) | Forced return without remaining execution; agree frame, value type and effect log |
| clear() | Individual/group removal or leaving with | Remove from ordinary use; separate fault-guard control |
| case(...) | @test(...) | Rename decorator and validate callable shape early |
| record()/records() | Same methods plus explicit snapshot conversion | Preserve runtime journal; no implicit automatic export |
| config | settings | Immutable effective captured settings with defaults |
| config_props | sources | Immutable original data without defaults, sha256 and reference by role |
| No separate method | resume(...) | Continue to the next stop and return its description |
| No separate method | step(...) | Bounded steps: instruction/source and into/over |
| No separate method | watch(...) | Data-access point with explicit read/write and hardware limits |
| No separate method | finish(*, frame=...) | Natural return of an existing invocation and available value; current invocation by default |
| No separate method | until(location=None, ...) | Navigation within the current invocation; agree GDB semantics with and without location |
| No separate method | call(...) | Additional firmware call initiated by the scenario, distinct from finish/ret |
| Direct gdb.execute(...) | execute(command) | Explicit GDB command access with logging and invalidation rules |
| Direct GDB frame access | context(...)/frames(...) | Shared snapshot/frame-reference model for reading, navigation and return |

return, break and continue are Python keywords; ret, breakpoint and resume are selected.
code_point is not used. run_to becomes reach in the proposed surface. Keeping the name
reach does not retain its old embedded-check semantics.

## Distinctions contracts must preserve

resume awaits the next stop; reach targets a location without the current-invocation
boundary. Do not hide foreign stops by automatically continuing. until has distinct GDB
semantics: the no-location form is not simply the next textual line. Verify addresses,
lines, loops and frame exit separately; target_reached/frame_exited/interrupted names
are not yet approved. finish executes remaining code, ret skips it, call creates a new
invocation. The default finish frame is intended to be the innermost invocation; explicit
older frames and frame kinds need separate validation.

Do not turn read into an unrestricted evaluator while promising safe reads. Agree RAM,
MMIO, pointers, locals, CPU registers and evaluator effects. Historical snapshots,
managed resource handles and lifetime-bound FrameRefs are different entities. Control
operations return actual outcomes and scenarios assert expectations; execution errors
must not be disguised as ordinary results. External timeout may prevent a return value;
runner ERROR/recovery remains separate.

## Work stages

- [x] Record 0.3.0 target and names for design.
- [x] Consolidate baseline audit, accepted requirements and coverage gaps: arguments,
  results, errors, side effects, resources, cleanup and compatibility. Reuse existing
  evidence; repeat only for changes or new assertions.
- [ ] Classify each table entry as replacement, extension, technique or retained API;
  justify every compatibility break.
- [ ] Define value/stop/mutation/handle/frame models, read/check/record bridge, serialization
  and bounds. Use session.toml/api.toml with explicitly agreed schema and migration.
- [ ] Agree exact per-operation contracts: signatures/defaults, state, types/ranges,
  FAIL/ERROR, partial effects and recovery. Resolve both until variants and execute
  invalidation/resource ownership.
- [ ] Approve API-spec revision and linked system requirements, test cases and traceability;
  distinguish API, agent, runner and report responsibilities.
- [ ] Create local prototypes and paired old/new scenarios; assess readability, diagnostics,
  service-code cost, time and memory.
- [ ] Run host/offline GDB checks and affected operations on five stands: F030R8,
  BluePill-Plus F103, F401CC, F411CE and F429I-DISCO. Validate new MCU/backend/ABI limits
  and recovery/restoration; historical HW PASS does not accept a new implementation.
- [ ] Accept 0.3.0 scope and migration, then separately authorize core integration.
  Explicitly defer remaining candidates rather than promising all capabilities at once.
- [ ] Migrate production scenarios, RU/EN reference, migration guide, CHANGELOG and release
  acceptance. Tagging and publication require a separate owner decision.

## Compatibility and acceptance

Pre-1.0 breaks are allowed when benefits are justified and migration documented. Choose
between temporary adapters and immediate removal, with an agreed schedule. Check both
consumer source and scenarios inside existing run packages: unpacking does not prove API
compatibility. Do not silently reinterpret unknown fields of an old configuration schema.

Criteria: clear purpose, composability, trustworthy reports, explicit effects, controlled
resources, predictable errors, no hidden resume/retry and sufficient positive/negative
coverage. Shorter names or fewer lines alone do not justify replacement. Explicitly agree
any lost capability.

Research plans, prototypes and raw results stay local under [maintenance](maintenance.md).
This public plan records the accepted target and design surface; public contracts and
accepted conclusions must not link to local research material.
