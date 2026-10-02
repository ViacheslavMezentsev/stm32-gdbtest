# API scope proposal based on R1–R18

[Documentation](index.md) · [Русский](../ru/api-proposal.md)

2026-10-02. Status: **discussion draft; contracts are not approved**.
The owner requested a separate stack/caller group; this extends the discussion
scope and does not authorize implementation.
Branch `codex/rc3-api-r1`. Based on the [report summary](summary.md),
[tool classification](scenario-tools.md) and [context proposal](execution-context.md).
This proposes a public surface, not an implementation. Current
[API_VERSION=1](../../../en/API.md), specification and core code remain unchanged.
HW, including RTOS, is paused; [technical debt](technical-debt.md) remains open.

## 1. Recommended approach

Extend the scenario's `Target` with small operations returning data and explicit
stop results. Composition remains ordinary Python. A class, loop or peripheral
does not need its own API class: expressions, frames, points and bounded execution
control provide the mechanisms for testing them.

The three packages below define discussion and possible implementation order,
not a promise to include everything in rc3: **A** observation, **B** points and
navigation, **C** intervention. New names/signatures are provisional. A mature
GDB mechanism does not imply a ready general stm32_gdbtest contract.

## 2. Preserve the existing API

`check`, `value`, `fields`, `reach`, `breakpoint`, `set_value`, `force_return` and
`clear` retain parameter meanings, result types and error behavior. In particular,
`value(expression)` remains integer-oriented; richer reads get a separate name.
Do not redefine `clear()` to remove only new points: its current semantics include
Target fault guards.

New navigation must not silently change `reach()`. Old scenarios require regression
on new versions in previously supported configurations. API_VERSION, schema and
migration decisions accompany approval of concrete changes, not this documentation
edit. Preserving old methods does not make new scenarios work on old modules.

## 3. Package A: observation and evidence

| Candidate | Contract for discussion | Evidence |
| --- | --- | --- |
| `t.context(*, registers=(), max_frames=8)` | Immutable snapshot: `context['PC']`, SP, stop, frames, meta, availability; no continue or implicit MMIO | [R1](r1.md), [R11](r11.md), [R15](r15.md); general contract: D4 |
| `t.read(path, *, frame=None)` | Typed symbol/field/index or local snapshot in a selected FrameRef; bounded depth/size, no function calls | [R1](r1.md), [R6](r6.md), [R18](r18.md) |
| `t.evaluate(expression, *, frame=None)` | Explicit C/C++ evaluator with typed result; not declared safe reading; potentially effectful evaluation invalidates previous freshness | [R2](r2.md), [R3](r3.md); limitations below |
| `t.resolve(location)` | All concrete addresses/symbols/source positions for a function, full C++ signature, file:line or address; no silent first-location selection | [R15](r15.md), [R18](r18.md) |
| `t.disassemble(address, *, count=1)` | Bounded address/length/asm sequence; machine bytes as an explicitly requested addition | [R2](r2.md), [R16](r16.md); self-branch recognition remains a technique |
| `t.capabilities()` | Operation availability and limits for current MCU/GDB/backend/ABI, with provenance | [R7](r7.md), [R8](r8.md), [R17](r17.md), [R18](r18.md); not just GDB version checking |
| `t.record(name, data)` | Public bounded recording of materialized evidence without internal `t.report` access | [R1](r1.md); validate serialization, size and duplicate names |

Minimal discussion core A: **context, read, resolve, record**. Disassemble is a
useful small independent primitive. Capabilities is needed before portable B/C
claims: distinguish mechanism availability, verification on this configuration,
known rejection and untested status rather than collapsing these axes into one
supported boolean.

`read` deliberately does not accept all C syntax. `evaluate` cannot promise no
side effects through string inspection or merely banning `=`: MMIO, overloaded
operations and calls remain possible. Recommendation: exclude inferior calls from
ordinary evaluate, expose them through `call`, and keep arbitrary evaluation an
explicit advanced operation with documented boundaries. If the prohibition cannot
be enforced reliably, do not publish that contract. Until resolved, current `value`
and raw GDB retain their existing limitations. Base context never uses evaluate.

### 3.1. Frame stack and calling context

Include explicit frame operations in A. Consumer foundations already exist:
[Research.frames/frame/local](../../../../tests/api-experiments/lab/session.py)
and [caller_is](../../../../tests/api-experiments/lab/navigation.py).
[R2](r2.md) compares the helper with `$_caller_is`, [R6](r6.md) tests recursion,
and [R15](r15.md) inline frames. These prove individual mechanisms; the general
interfaces proposed below are not implemented.

| Candidate | Contract for discussion |
| --- | --- |
| `t.frames(*, max_depth=8)` | StackSnapshot: innermost-to-outermost frames, run/stop/revision, complete and termination_reason. Reasons: stack_end, depth_limit, unwind_error; never present partial stacks as complete |
| `t.frame(index=0, *, stack)` | FrameRef from the supplied snapshot without changing GDB selected frame. Index 0 is the innermost represented frame, including inline; invalid index is an explicit error |
| `t.read(path, *, frame=ref)` | Previously proposed typed local/argument/this read in a particular frame; no fallback to a same-named global when a local is absent |
| `t.arguments(*, frame, max_items=32)` | Bounded named argument snapshot with types/availability; explicitly mark incomplete enumeration |
| `t.locals(*, frame, max_items=32)` | Visible locals in current lexical scope with symbol descriptions; shadowing must not silently lose values. Settle key/symbol-list representation before implementation |
| `caller_is(stack, name, *, depth=1)` | Ready-made helper: exact name at one specified depth from frame 0; depth ≥ 1. Analog of the studied `$_caller_is`, not an all-ancestor search |
| `find_caller(stack, name, *, max_depth=8)` | Ready-made helper: nearest matching ancestor at depths 1…max_depth; return FrameRef or None only after fully searching the requested range/reaching stack end |

Target methods are primitives; both caller helpers are library techniques over a
snapshot without further MCU reads. Match function names exactly, including the
signature when supplied by GDB; do not implicitly normalize C++/clone names or
enable regex. Recursive matches remain distinct frames; find_caller selects the
nearest, while scenarios filter the frame list to obtain all matches.

`caller_is` returns False on a known mismatch or proven stack end before the requested
depth. If capture stopped earlier at a limit/unwind error, the result is unknown:
raise an incomplete-stack error rather than False/None. find_caller may return an
already found nearest ancestor when the path to it was read completely; no match
within max_depth says nothing about more distant ancestors.

Initial depth semantics count **all GDB-represented frames**, including inline/dummy;
helpers never silently skip them. Distinguish frame kind and name/argument
availability; an unavailable name on the search path is not a proven mismatch.
Tail calls, IRQs and damaged stacks may affect completeness/representation; R6
does not prove full support. t.frames and context['frames'] share frame, ordering
and completeness models. FrameRef exposes no live gdb.Frame: fresh reads using
stale refs after resume/mutation are rejected, while snapshot data stay readable.
Choosing a frame never changes physical context['PC'].

**Pseudocode, not current API:**

```python
stack = t.frames(max_depth=16)
current = t.frame(0, stack=stack)
depth = t.read('depth', frame=current)
is_beta = caller_is(stack, 'route_beta', depth=3)
ancestor = find_caller(stack, 'route_beta', max_depth=8)
# A displayed backtrace uses the same immutable stack.frames records.
```

This shows the **current call chain** (backtrace), not every call made during a run.
A frame list suffices for one stop; no separate graphical viewer is proposed.
A dynamic call tree needs entry/exit recording, missed-event handling, recursion,
IRQs and overhead accounting; no such tool exists here yet. A static possible-call
graph from source/ELF is another separate task. Both graphs are outside the initial
API; potential future demand is recorded as debt D14.

Before implementation verify exact depth/search, absent callers, depth_limit and
unwind_error, unavailable names, recursive/inline frames, shadowing, optimized_out,
stale refs and no selected-frame side effects. This extends D4/D10 without resuming
experiments.

## 4. Package B: resources and navigation

| Candidate | Contract for discussion | Evidence |
| --- | --- | --- |
| `t.code_point(location, *, temporary=False, condition=None, ignore_count=0)` | Owned PointHandle with context manager and explicit remove; hardware-only, one resolved location by default; multiple locations require explicit selection | [R2](r2.md), [R8](r8.md), [R15](r15.md) |
| `t.watch(address, size, *, access='write')` | Owned hardware point on explicit range; read/write/access, alignment and actual insertion checked; no silent software fallback | [R3](r3.md), [R7](r7.md), [R12](r12.md) |
| `t.resume(*, timeout_s)` | Continue to first stop and return StopResult; no automatic bypass of foreign points | [R1](r1.md), [R9](r9.md), [R16](r16.md) |
| `t.run_to(location, *, timeout_s)` | Owned temporary point plus continuation; OperationResult distinguishes target_reached from another stop | [R2](r2.md), [R8](r8.md), [R16](r16.md) |
| `t.finish(*, frame=None, timeout_s)` | Naturally finish selected invocation; ReturnResult includes typed value when available; reserve service-point headroom | [R5](r5.md), [R6](r6.md), [R17](r17.md), [R18](r18.md) |
| `t.step(*, unit='instruction', over=False, count=1, timeout_s)` | Bounded steps; foreign breakpoint interrupts operation and returns control to author | [R2](r2.md), [R16](r16.md); native regression [R4](r4.md) remains D6 |
| `t.advance(location, *, timeout_s)` | Continue with current-frame boundary; frame_exited differs from target_reached | [R16](r16.md); include only if this semantics is needed separately from run_to |

Initial B: **code_point, resume, run_to, finish, instruction step**. Watch is a
separate capability with backend limits. Source step and advance are later
discussion scope; bare until remains debt. Initial conditions are GDB expressions,
not callbacks capable of recursively resuming execution. `ignore_count` counts
skipped hits, not application iterations.

PointHandle owns a resource, unlike a snapshot: operations reject deleted handles;
events save temporary point numbers before deletion. Budgets count physical
locations, fault guards and internal finish/call points. Creating a handle does
not prove MCU insertion before continue. Automatic watch-range splitting and slot
allocation remain techniques for now.

## 5. Package C: intervention with explicit boundaries

| Candidate | Recommendation and limitation | Evidence |
| --- | --- | --- |
| `t.read_memory(address, size)` / `t.write_memory(address, data)` | Bounded consumer RAM region, write log and range checks; not a general MMIO API | [R1](r1.md), [R4](r4.md) |
| `t.call(expression, *, timeout_s)` | Explicit firmware execution; ReturnResult distinguishes completion/interruption; only declared ABIs and limits | [R5](r5.md), [R9](r9.md), [R10](r10.md), [R17](r17.md), [R18](r18.md) |
| Typed forced return | First define permitted forms alongside existing force_return; no silent behavior change | [R5](r5.md), [R18](r18.md): no universal aggregates promise |
| Register writes, PC/jump | Exclude from initial scope; needs a separate stack/control-flow effects model and checks | Read/step availability does not prove arbitrary PC transfer correctness |

Call is not transactional: RAM/peripherals may change even without a result.
Never automatically retry interrupted calls; return control with stop state.
External timeout may prevent Python returning any ReturnResult: host records ERROR
and performs separately agreed recovery. Forced return skips the body and does
not prove aggregate delivery to caller. Pinned-ELF hidden-sret workarounds remain
consumer techniques.

## 6. Shared result models

| Model | Minimum content and lifecycle |
| --- | --- |
| Context | [Proposed schema](execution-context.md): immutable PC/SP, bounded frames, run/stop/revision, availability; readable after resume |
| FrameRef | Particular frame reference within run/stop/revision with index/kind; not just name/PC identity; interventions validate freshness |
| StackSnapshot | Immutable frames, run/stop/revision, complete/termination_reason; incomplete unwinding retains available frames and diagnostics |
| ValueSnapshot | type, width, kind, value, availability, provenance; bounded structures/arrays; void differs from missing result |
| StopResult | Actual event, all point numbers, signal, Context; does not itself mean scenario PASS |
| OperationResult | requested operation, outcome, StopResult; distinguish completed/target_reached, interrupted and frame_exited; require_completed() can explicitly reject incomplete execution |
| ReturnResult | OperationResult plus ValueSnapshot; natural finish and direct call retain different operation kinds |

Type names are provisional too. Recommendation: ordinary unexpected points return
interrupted in the new low-level API; fault, connection loss, unavailable operations
and timeout must not masquerade as completed. Operation exceptions carry available
diagnostics/StopResult. Scenario expectation mismatch is FAIL; inability to perform
an operation is ERROR. An expected research ERROR never becomes PASS for the
original run. Exact error hierarchy is decision Q3.

## 7. Composition example for discussion

**Proposed API pseudocode; not executable now.** It waits for natural
MX_SPI1_Init entry and exit rather than invoking the function additionally.

```python
entry = t.run_to('MX_SPI1_Init', timeout_s=5)
entry.require_completed()
before = entry.stop.context
finished = t.finish(timeout_s=5)
finished.require_completed()
t.record('spi_init', {'entry_pc': before['PC'],
                      'return_pc': finished.stop.context['PC']})
# Consumer assertions must verify the required SPI configuration here.
```

Reaching exit does not prove correct SPI configuration: consumers specify expected
values and permissible register reads. Operation limits are capped by remaining
case budget; two five-second timeouts do not extend the external watchdog.
Example syntax belongs to Q1/Q3 discussion, not current API documentation.

## 8. Keep as techniques and patterns

Caller-is and recursion filters are helpers over frames; infinite self-branch
detection recognizes instructions; counter deadlines combine expressions and
observation; patch/restore composes RAM operations; out-buffer/status replacement
intercepts entry and verifies caller; failure/success sequences form a finite
expectation state machine. Techniques need examples, preconditions, cleanup and limits.

Patterns such as error-branch verification, accepted-state retention and peripheral
transfer checks compose these techniques. DMA/IRQ/WFI, MCU registers and future
RTOS tasks remain consumer profiles/libraries. Host recovery does not become a
synchronous GDB method. Universal `cmds('...; ...')` is unnecessary as the main API:
Python composition preserves individual results and failure boundaries.

## 9. Questions and recommended decisions

All rows are **open**; recommendations are not owner decisions.

| ID | Question | Recommendation for discussion |
| --- | --- | --- |
| Q1 | Flat Target or t.execution/t.memory/t.points? | Flat methods and separate result types for now; introduce namespaces when complexity warrants them |
| Q2 | Initial scope? | A: context/read/resolve/record/disassemble plus frames/frame/arguments/locals and caller helpers; B next, C separately; capabilities before claiming B/C support |
| Q3 | Unexpected stop: exception or result? | Low-level interrupted result, explicit require_completed; infrastructure/fault errors raise with diagnostics |
| Q4 | C expressions and side effects? | Separate bounded read, advanced evaluate and call; no universal read-only evaluator promise |
| Q5 | Automatically choose multiple locations/split watch ranges? | No; explicit resolution/selection, technique composition and physical budget accounting |
| Q6 | Approve context as dict? | Read-only Mapping with familiar ['PC']; immutable nested structures, separate export copy |
| Q7 | Untested configuration? | No support claim; retain unverified status and diagnose limits before intervention where possible |
| Q8 | Include aggregate forced return/RTOS now? | No; known FAIL and paused debt prevent a general promise |
| Q9 | Caller semantics and stack completeness? | Exact depth separate from nearest-ancestor search; count all represented frames, never turn incompleteness into False; historical tree outside initial scope |

Start discussion with **Q2 and Q6**: approve minimum observation scope and context
shape, then Q3 for navigation. Record decisions here with date and owner's wording,
then refine contract proposals. Only separate implementation authorization starts
core, specification, migration and required regression changes. Authorization to
discuss API does not resume hardware experiments.

Before selecting implementation scope agree [evolution rules and specification boundaries](api-evolution.md).
