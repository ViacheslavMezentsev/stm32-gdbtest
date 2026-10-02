# Scenario tools: API, techniques and patterns

[Documentation](index.md) · [Русский](../ru/scenario-tools.md)

Classification proposal based on [R1–R18](summary.md), 2026-10-02. Candidate labels
describe semantics, not approved new method names. The current
[API](../../../en/API.md) remains unchanged.

## Three layers

| Layer | Contents | Example and responsibility |
| --- | --- | --- |
| API | One operation with explicit inputs, result, effects and failures | Read a value, install a point, capture a snapshot; core owns contract and resource ownership |
| Technique | Reproducible composition with preconditions, checks and cleanup | Wait for natural entry, replace out-buffer/status, verify caller and next natural call |
| Scenario pattern | Several techniques organized around tested behavior | Supply an error/success sequence and verify retention of accepted state |

“Paradigm” is a broader approach, such as DDTT; “scenario pattern” is more precise
for this catalog. Not every pattern belongs in core. Techniques may live in consumer
libraries; patterns in examples with explicit application expectations. Separate
mechanism from policy: frame access is more general than requiring a function to
be called only from a particular handler.

## Application areas

| Area | Verified tools | Techniques → patterns | Limitation |
| --- | --- | --- | --- |
| C: expressions, structures, arrays, macros | parse/eval, sizeof, fields/indices, typed snapshots (R1–R5) | Capture inputs/outputs → function contract | Current value returns int; arbitrary C expressions can have side effects |
| C: loops, branches, progress | Point conditions, counter, until/advance, forced return (R2–R4, R16) | Bounded wait; status replacement selecting a branch → error handling | Iteration count is not wall-clock timeout; forced exit skips the body |
| Functions, stack, recursion | finish/call, caller walk, frames, scalar ABI (R5–R6, R9, R17) | Select a particular call, observe natural result → caller/callee contract | call executes firmware and mutates state; dummy call differs from natural invocation |
| C++: methods and objects | this, const overloads, full signature, aggregates/HFA (R18) | Select overload and verify object/sink → method contract | Not general class coverage: virtual/lifetime/exceptions untested |
| Optimized code | INLINE_FRAME, locations, scope, optimized_out (R15–R16) | Correlate symbols, instructions and final sink → result verification independent of locals | Line/name/PC alone are ambiguous |
| Assembly and ABI | disassemble, stepi/nexti, registers, stack arguments (R2, R4, R16–R18) | Recognize self-branch; verify BL/return boundary → machine contract | Assembly syntax and ABI depend on build; native stepping regression remains open |
| RAM and CPU accesses | Bounded patch/restore, watch/rwatch/awatch, range splitting (R1, R3–R4, R7) | Check access instead of change; inject input bytes → data handling | RAM restore cannot undo external effects already produced |
| MCU: IRQ, DMA, timers, Sleep | Registers/flags, IRQ sentinel, hardware frame, WFI (R10–R13) | Observe DMA completion before CPU read; separate wakeup from ticks → transfer/wakeup contract | Requires profile and ordinary firmware; no universal peripheral snapshot |
| Experiment control | Stop identity, ownership, FPB/DWT budget, evidence, timeout/recovery (R1, R7–R10, R14) | Control stop, cleanup and natural control → reproducible bounded scenario | External kill needs host recovery; reliability of all combinations is unproven |

## Candidate placement

Labels: **existing** means public API; **candidate** means proposed primitive;
**technique** means composition; **pattern** means scenario objective. A GDB
primitive does not become stm32_gdbtest API merely by being available in Python.

| Tool | Category and proposed placement | Basis |
| --- | --- | --- |
| check, value, fields, reach, breakpoint, set_value, force_return, clear | Existing; retain documented contracts | Current API; additions must not silently change old results |
| Typed reads and context/stop snapshots | Observation API candidates | R1, R11, R15–R18; [context proposal](execution-context.md) |
| Location resolution, owned breakpoint/watchpoint, resource budget | Resource API candidates | R2, R7–R8, R15, R18; pending/multiple locations and insertion rejection must be explicit |
| Continue to event, instruction step, natural finish | Execution API candidates returning stop results | R2, R9, R16; early frame exit/foreign point is not target arrival |
| Function call and typed result | Conditional intervention API candidate | R5, R9–R10, R17–R18; needs ABI/capability and interrupted/fault/timeout states |
| Bounded RAM read, write/restore | Primitives are API candidates; patch/restore is a technique | R1/R4; do not extend rollback to MMIO or arbitrary execution |
| Caller predicate, recursive frame selection, self-branch | Techniques over frames/instructions; possible library helpers | R2/R6; depth limit, frame kind, architecture |
| Progress counter, range splitting, finish headroom | Techniques over expressions/resources | R3/R7/R8; wrap formula, range coverage, physical slots |
| Out-buffer + status; finite interception sequence | Techniques; error-branch and accepted-state-retention patterns | R4/R14; consumer specifies data, order and expected sinks |
| Hidden-sret write on pinned ELF | Narrow ABI technique, not generic structure-return API | R5/R18; do not conceal known FAIL using a guessed layout |
| IRQ/DMA/WFI diagnostics | Profile techniques; peripheral contract patterns | R11–R13; ordinary firmware, MCU registers and control stops |
| GDB commands, macro/define, Python if/else | Low-level composition tools; consumer helper | R3; C expressions obtain firmware values, scenario logic stays in Python/GDB |
| Fault sidecar, timeout recovery | Host orchestration technique, not synchronous GDB helper | R10; retain original ERROR report |

## Future API properties and acceptance criteria

| Property | Testable rule |
| --- | --- |
| Simplicity | One operation has one meaning; ordinary scenarios need no raw GDB, internal Target fields or CLI-output parsing |
| Backward compatibility | Old scenarios work on new versions in previously supported configurations; old API regression is mandatory. New features on old versions are explicitly unavailable, not simulated |
| Unambiguity | Natural finish, forced return and direct call are distinct; results identify actual reason/location rather than only boolean; multiple locations are not randomly selected |
| Parameterization | Explicit location/frame/condition, time/step/byte/depth limits and unexpected-stop policy; validate before intervention where possible |
| Types and availability | Preserve type/width/signedness; missing, optimized_out and unreadable never become 0/False |
| Composition | Results support techniques; resource handling is separate from application expectations; no implicit continue |
| Boundedness | Every wait has a bound; budgets include physical locations and service points; external watchdog remains the final boundary |
| Ownership and restoration | Remove only owned resources; restore settings; retain both primary and cleanup failures. Do not promise transactional execution rollback |
| Observability | Snapshots identify stop/image; reports distinguish expected rejection, FAIL and ERROR, retaining intervention before/after |
| Honest portability | Support depends on operation, MCU, backend, GDB and ABI/build; version number alone never makes an unknown combination verified |
| Extensibility | Additive optional fields and schema version; semantic changes require migration. MCU policy stays with consumers; raw GDB is documented separately as leaving wrapper guarantees |
| Thread and lifecycle | Main GDB thread only; live handles do not survive resume/reset; immutable evidence remains readable later |

Proposed discussion order: observation/context and stop reasons → resources and
navigation → intervention with explicit ABI boundaries → technique library and
pattern examples. Implementation requires scope approval; untested combinations
remain in the [debt register](technical-debt.md).
