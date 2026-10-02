# rc3: Target API extension research

[Documentation](index.md) · [Русский](../ru/RC3_API_RESEARCH.md)

[R2: navigation, calls and watchpoints](RC3_API_R2.md): 56/56 HLA and 8/8 native DAP; core promotion requires explicit owner approval.

Date: 2026-10-02. Base: `da42cd74c27a01c21df47cd660e2533e9bcfc6d4`;
branch: `codex/rc3-gdb-python-research`. Target: **0.1.0rc3**.
This is research and an experiment plan, **not an implemented API or hardware acceptance**.
Method names are provisional. The Python package remains `0.1.0rc2`, `API_VERSION=1`,
specification 0.58. This document changes no normative requirements or schemas.

## Conclusion and recommended scope

The useful abstraction is a composition of operations: **observe → stop on a condition →
change an input/result → resume → check consequences → restore**.
Prioritize typed data and memory, structured stop reasons, explicit breakpoint/frame
lifetimes and public evidence recording. Then add hardware watchpoints and call
interception scenarios. Arbitrary target calls, asynchronous control and RTOS support
need separate experiments and need not block the first useful rc3 feature set.

- **P0:** `record`, value/frame snapshots, bounded RAM reads, `run_until` with a
  verifiable stop reason, resource ownership and capabilities.
- **P1:** stepping/finish after verifying breakpoint placement, hardware watchpoints,
  call history, arguments/output buffers, return sequences, parameters and independent oracles.
- **P2:** direct calls, C++/float ABI, timed execution with interruption and RTOS.
  Each may remain experimental beyond rc3.
- **Outside initial rc3:** reverse execution on real STM32, a universal DMA write
  trace, power/instrument control, arbitrary PC replacement, a generic target
  allocator and custom unwinding.

## 1. Project sources and existing techniques

| Source | Purpose |
| --- | --- |
| [API](API.md), [Target](../../stm32_gdbtest/target.py), [agent](../../stm32_gdbtest/agent.py) | Public operations, execution, results and teardown |
| [Test authoring](TEST_AUTHORING.md), [TECH-001…009](TESTING_TECHNIQUES.md) | Context, IRQ, injection, vectors and Sleep |
| [Contracts](CONTRACTS.md), [macros](HAL_MACRO_GUIDE.md), [compatibility](../../stm32_gdbtest/compatibility.py) | ELF/preflight, source review and existing API presence checks |
| [CMSIS reconciliation](CMSIS_ACCEPTANCE.md), [HAL GPIO/RCC](F030_HAL_GPIO_RCC.md) | Migration coverage and hardware evidence boundaries |
| [Checks](testing.md), [rc2 acceptance](RC2_READINESS.md) | Offline/HW, recovery, restoration and preserving errors |

An AST inventory of this base found **24 files with 121 `@case` decorators**:
98 CMSIS (18 F030 and 20 each F103/F401/F411/F429), 22 HAL F030 and one minimal
consumer. IDs repeat across profiles: this counts profile/scenario combinations,
not globally unique IDs or coverage. Reviewed implementations include boot/GPIO/clock,
ADC/DMA, numerical vectors, RTC/deadline, Sleep and HAL injections.

| Technique and example | Existing ability | API gap |
| --- | --- | --- |
| TECH-001/002, [F103 RTC](../../tests/firmware/profiles/f103c8/tests/board/test_rtc.py) | Save address/mask before changing macro context | No typed snapshot or explicit context object |
| TECH-003, [HAL runtime](../../tests/hal-f030/hal_scenarios/peripheral_runtime.py) | Await callback/IRQ, check handle and publication | No common count/order expectations |
| TECH-004/005/009, [GPIO/RCC](../../tests/hal-f030/profile/tests/board/test_hal_methods.py) | Conditional reach, NULL argument, forced return | No managed interception sequence, argument capture or output buffer |
| TECH-006, [F411 ADC](../../tests/firmware/profiles/f411ce/tests/board/test_adc.py) | MMIO injection, guard and timeout | `set_value` before/after reads cannot be generalized to W1C/WO/read-to-clear |
| TECH-007, [F030 vectors](../../tests/firmware/profiles/f030r8/tests/board/test_ci.py) | Replace natural-call arguments, independent vectors | `value` converts to int; no arrays, strings, float or structure snapshots |
| TECH-008, [F411 Sleep](../../tests/firmware/profiles/f411ce/tests/board/test_sleep.py) | Direct frame walk and WFI check | No public backtrace/disassembly; scenarios write internal `report` |

`check` already accepts Python objects comparable with `==`; scalar limitations
mainly come from `value/fields`. JSON compatibility remains the caller's responsibility.
`value` is a general GDB evaluator: expressions may call functions or write data.
Its name does not guarantee a pure read. `breakpoint` returns a live GDB object;
`reach` verifies a function name, so file:line/address support needs a new contract.
`clear` also deletes fault-handler breakpoints. Its budget counts valid Target
objects, not all actual hardware locations, external or internal breakpoints.

## 2. GDB manual: version and reading map

The owner supplied [gdb.pdf](gdb.pdf), retained unchanged in its original location.
Title: **GDB 19.0.50.20260922-git**, 1006 PDF pages.
SHA-256: `4f1dc20f2053dfe96a9db5e2f4f34a4398f67b72072609a01f468f031219d4b2`.
This development manual does not establish availability in the installed toolchain.
The table uses physical PDF pages, numbered from 1; printed pages here are 18 lower.
The Python part of chapter 23 and related sections were reviewed.

| Section | PDF / printed pages | Use |
| --- | --- | --- |
| Extending GDB; Python | 417; 427–556 / 399; 409–538 | Extension model and boundaries |
| Basic Python, Threading, Exceptions (§23.3.2.1–3) | 430–437 / 412–419 | execute, parameters, exceptions, main thread |
| Values, Types (§23.3.2.4–5) | 437–450 / 419–432 | Types, fields, arrays, strings, lazy values, assign |
| Pretty-printers, frame filters, unwinders, xmethods | 450–475 / 432–457 | Diagnostics/context extensions, not correctness oracles |
| Inferiors, Events, Threads (§23.3.2.17–19) | 475–487 / 457–469 | Memory, stops, thread selection |
| Recordings; CLI/MI; Parameters | 487–503 / 469–485 | Backend limits, commands and parameters |
| Frames, Blocks, Symbols, line tables (§23.3.2.28–32) | 510–522 / 492–504 | Arguments, scope, PC, DWARF and source positions |
| Breakpoints, FinishBreakpoints (§23.3.2.33–34) | 522–528 / 504–510 | Conditions, resources, completion and return value |
| Architecture, registers, connections, disassembly | 532–546 / 514–528 | Structured registers/instructions and separate UI extensions |
| Auto-loading | 552 / 534 | Retain explicit agent loading and disabled auto-load |
| Watchpoints; Continuing/Stepping; Returning/Calling | 86; 103; 302–306 / 68; 85; 284–288 | Observation, stepping and inferior-call semantics |

### Constraints that affect design

1. **Do not inject inside `Breakpoint.stop()`.** PDF p524 prohibits changing
   execution, frames, breakpoints and generally data there. The callback decides
   whether to stop and captures bounded observations. A main-thread dispatcher
   writes, returns or resumes after `gdb.execute` returns. Do not copy unrestricted
   callback interception from another framework.
2. **Events are not a hardware trace.** `memory_changed/register_changed` describe
   changes made by the GDB user, not every CPU/DMA write (PDF p481). DMA may continue
   while the CPU is halted; multiple reads are not an atomic snapshot.
3. **Finish is not necessarily hardware-only.** `FinishBreakpoint(frame, internal)`
   has no hardware-type argument; finish/next/until may use internal breakpoints.
   Prove placement before claiming compliance with the no-Flash-breakpoint policy.
   `return_value=None` means void or unavailable; inline frames are unsupported,
   and `out_of_scope` is not a normal return (PDF pp527–528).
4. **Calls change the MCU.** Dummy frames, ABI, interrupts, stack changes and hangs
   matter. Unwinding does not roll back memory/peripherals. New call timeouts depend
   on asynchronous targets; an external host timeout and recovery remain necessary.
5. **Watchpoints depend on the target.** `watch` detects value changes, whereas
   `awatch` may detect same-value accesses. Check width/alignment, resources and
   actual insertion at resume; prohibit silent software fallback. DMA observation
   needs its own experiment, independent of CPU-watchpoint success.
6. **Live objects are not snapshots.** Frame/Value/Breakpoint may become invalid
   after resume/reset; lazy values may be read later than intended. Serialize
   materialized data with a stop ID rather than retaining live objects.
7. **Main thread and deadlines.** `post_event` provides no execution deadline.
   Python workers must not call `gdb.execute/parse_and_eval`. Even the documented
   thread-safe `interrupt` in newer GDB does not override the project's current
   threading policy: changing that model needs a separate design decision.

### Completed experiment without an MCU

On 2026-10-02 the [probe](../../tools/research/gdb_api_probe.py) ran with `-nx -nh -batch`,
without an ELF, server or target connection. See the [machine-readable result](../research/rc3-gdb14-capabilities.json).
Environment: GDB **14.2.90.20240526-git**, embedded Python **3.11.4**,
xPack GCC13.3.1-1.1, Windows.

| Check | Result |
| --- | --- |
| Frame/read_var/read_register/older, Inferior read/write/search_memory, disassemble | Attributes present; hardware semantics untested |
| Breakpoint.locations, FinishBreakpoint/return_value, events.stop/cont | Present; insertion and stops untested |
| with_parameter, post_event, Thread, blocked_signals | Present |
| Value.bytes, Value.is_unavailable, gdb.interrupt | Absent |
| direct-call-timeout, indirect-call-timeout, unwind-on-timeout | Parameters absent |
| may-call-functions / non-stop | true / false in clean GDB |
| `int(gdb.Value(3.5))` / `float(gdb.Value(3.5))` | 3 / 3.5, confirming fractional loss in the current approach |

Repeat with each toolchain's Python-enabled GDB:

```text
<GDB> -nx -nh -batch -ex "set auto-load off" -ex "source tools/research/gdb_api_probe.py"
```

The probe prints `RC3_PROBE=<JSON>` and connects to nothing. Attribute presence is
only L0. L1 means ELF operations without a target; L2 means semantics on a specific
MCU/backend; L3 means repeatability, failure paths and recovery. Capabilities need
these levels and unavailability reasons, not just a GDB version check.

### Additional xPack GCC15 check

Following the owner's update, installed xPack GCC **15.2.1-1.1** was checked:
GDB **16.3.90.20250906-git**, Python **3.13.12**.
The same probe produced this [L0 result](../research/rc3-gdb16-capabilities.json)
without an MCU. Compared with GDB14, `Value.bytes`, `gdb.interrupt`,
`direct-call-timeout`, `indirect-call-timeout` and `unwind-on-timeout` are present.
Parameter values are respectively `None` (unlimited), `30` and `false`.
`Value.is_unavailable` remains absent. This is not the manual's GDB19.

GDB16 is the preferred candidate for E15–17, but presence does not establish
async-target support, effective timeouts or permission to call GDB from workers.
First retain the same ELF and select GDB in the session (CLI `--gdb` applies only to packages); rebuilding with
GCC15 is a separate experimental variable. Keep global PATH and baseline GCC13
unchanged. Do not treat `Value.bytes` as generic raw target memory access with
arbitrary endianness either.

Stand update: the owner confirmed WeAct BluePill-Plus on J-Link CE, consistent
with the local F103/J-Link TOML. Local files map F411CE to ST-Link/OpenOCD with
ST-LINK GDB Server as an alternative. The owner mapped the second ST-Link to
Nucleo-F030R8; a local OpenOCD TOML was added. The old F030/J-Link TOML
references a probe absent from the current USB list.

## 3. Proposed API surface

All names below are **candidates**, not instructions for the current Target.

| Family | Candidates | Contract and new flexibility |
| --- | --- | --- |
| Evidence | `record(name, data)`, `snapshot(paths)` | JSON primitives, type/width, stop ID, size limits, protected reserved keys; no internal `t.report` access |
| Data | `read(path)`, `read_array(path, count)`, `read_string(path, max_bytes)` | int/bool/float/enum/pointer/structure; bounded depth/length, distinct NULL/unavailable, explicit NaN/Inf encoding |
| Memory | `read_memory(address, size)`, `write_memory(address, data)` | Materialized bytes, target range/endianness; initially writes only to agreed RAM; MMIO separate |
| Frames | `frames()`, `frame(index)`, `read_local(name, frame)`, `registers(names)`, `disassemble(address, count)` | PC/SP/type/frame/line/unwind-reason snapshot; restore temporary context selection, reject stale handles |
| Stops | `run_until(location, when=...)`, `resume_until(handles)` | StopRecord: expected/fault/signal/exit/unexpected; distinct function/file:line/address resolution and explicit ambiguity |
| Resources | `breakpoints.scope()`, managed handles | Delete only owned points, separate fault guards; actual locations, FPB/data-watchpoint budgets; fail without fallback |
| Steps/completion | `step_instruction`, `step_source`, `next`, `finish` | Defined operation and stop reason, bounded steps/deadline, verified return-point strategy |
| Mutation | `write(path, value)`, `override_return(value)`, `patch_ram(...)` | Type/ABI checks, RAM before/after, preserve attempts on error; rollback only where demonstrated |
| Data over time | `watch(path, access=...)`, `expect_sequence`, `capture_calls` | Watchpoint/call count/order/arguments; bounded history, not real-time trace or coverage |
| Call behavior | `intercept(function, actions=..., count=...)` | Main-thread dispatcher: snapshot → argument/output/return → resume; bounded recursion, IRQ and exhausted action list |
| Invocation/run | `call(function, args)`, later `run_for(...)` | Explicit action instead of hidden eval; defined state, timeout, IRQ, ABI and postcondition |
| Assertions | masked/range/approx/sequence predicates, vector IDs | Compare stored values without rereading MMIO; fail-fast default |

Keep `value` compatible by adding operations instead of changing its return type.
For `read(path)`, use restricted symbol/field/index paths through Symbol/Frame/Value;
arbitrary C expressions remain a separate expert escape hatch. `may-call-functions=off`
blocks calls, not assignments or MMIO side effects, and cannot prove expression purity.
Trusted scenarios can still `import gdb`; the wrapper is no sandbox and can log only
operations passing through it.

Snapshots capture selected values at one stop, without promising consistency with
running DMA. `patch_ram` restores only its own bytes, not the system. Avoid generic
MMIO read-modify-write/rollback: RW/W1C/rc_w0/WO/read-to-clear require register-specific
semantics and restoration. Profile schema1 has no RAM ranges or watchpoint budgets;
use experimental configuration first, then decide the schema explicitly.

Start the dispatcher with natural application calls. Interception inside a dummy
frame created by `call` is a separate experiment. A callback exception must produce
ERROR even if GDB merely prints the exception and continues.

## 4. Existing tools and useful models

Primary sources checked on 2026-10-02; borrow concepts, not code or dependencies.
None of the reviewed sources establishes a complete operation set for all
GDB/MCU/backend combinations. Completeness should mean coverage of required actions
and failures by experiments, rather than a method count.

| Source | Useful model | Difference from stm32-gdbtest |
| --- | --- | --- |
| [DOTT.NG overview](https://tw-ghub.github.io/dott-ng_docu/index.html), [developer guide](https://tw-ghub.github.io/dott-ng_docu/DeveloperGuide.html) | Closest analogue: halt/intercept points, calls and bulk memory | Host pytest + GDB/MI; documented helper library/test hook and callback limits. Retain our no-hooks rule |
| [gMock cookbook](https://google.github.io/googletest/gmock_cook_book.html), [actions](https://google.github.io/googletest/reference/actions.html) | Argument expectations, counts/order, action/return sequences | Compile-time mocks do not prove target interception feasibility |
| [pytest fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html), [parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) | Setup/teardown, scope and named vectors | Do not replace AST collection of `@case` with dynamic discovery without a migration |
| [Hypothesis stateful](https://hypothesis.readthedocs.io/en/latest/stateful.html) | Generated action sequences and model checking | Begin with deterministic replay, reset and bounded budgets; on-board shrinking is premature |
| [Zephyr Ztest](https://docs.zephyrproject.org/latest/develop/test/ztest.html), [Twister](https://docs.zephyrproject.org/latest/develop/test/twister.html) | Separate harness, build/board matrix and result | Tests often execute inside the target image; adopt organization, not architecture |
| [CMock](https://github.com/ThrowTheSwitch/CMock) | Generated C mocks/stubs | Different test binary construction; no ready replacement for debugger-driven testing |

Combine GDB mechanisms, gMock interaction expectations and pytest lifecycle ideas.
Model-based testing belongs above stable deterministic operations, not at the start.

## 5. Boards and experimental firmware

The owner offered **Nucleo-F030R8, WeAct BluePill-Plus v1.1 and WeAct BlackPill
F411CE/F401CC**, and authorized creating test projects from existing ones.
This identifies candidate boards, not their current connections or immediate Flash
overwrite approval. Before hardware execution, agree debugger/backend/SWD, exact
BluePill MCU (do not infer C8/CB from the board name), power and restore ELF/session.
F429 is outside this set; its existing examples provide ideas only.

| Stage | Board | Purpose and candidate backend |
| --- | --- | --- |
| A | BlackPill F411CE | Main M4/FPU: RAM, frames, stepping, calls; ST-Link/OpenOCD once confirmed |
| B | BluePill-Plus v1.1 | M3 and another debugger/backend: J-Link if confirmed; exact MCU before configure |
| C | Nucleo-F030R8 | M0, small breakpoint budget, expected limited data-watchpoints; ST-Link/OpenOCD once confirmed |
| D | BlackPill F401CC | M4 repetition on another profile/memory map; ST-Link/OpenOCD once confirmed |
| E | F411CE with another server | ST-LINK GDB Server on the agreed probe, sequentially; remote Linux later if needed |

Simultaneous board operation is unnecessary. Start with F411; F030/M3 establish
portability limits, F401 provides regression. Measure FPB/DWT resources and
rwatch/awatch availability; expected M0 limitations do not replace checking server behavior.

Proposed future project: `tests/api-experiments/`, an independent CMake consumer
using CMSIS startup/profiles from `tests/firmware`. A small ordinary application
contains arithmetic, structures, buffer processing, nested calls and a periodic IRQ.
Functions are called and retained naturally. No test hooks, special MCU-to-runner
commands or production-firmware changes. Python oracles use independent fixed vectors,
inputs and postconditions. Use an application-owned buffer with a phase excluding
CPU/DMA access, not arbitrary free RAM or GDB-invoked malloc.

Begin with `-Og -g3 -fno-lto` at compile/link; separately test `-O0`, `-O2` and LTO
as an availability matrix, not a way to conceal failures. Record actual F4 float
`-mfpu/-mfloat-abi` flags; separate soft/hard variants. Structure/64-bit returns are
not equivalent to int returns. Separate ordinary C++ methods/overloads from inline,
RTTI and exceptions. Add a later FreeRTOS program only if E18 needs it.

## 6. Experiment matrix

At the R0 review, **E01…E20 had not run on an MCU**. Subsequent results for an R1
subset are recorded in the [hardware protocol](RC3_API_R1.md). Start with host/fake-GDB failure paths, then
ELF/preflight, then one board. Record expected/actual results, failures and recovery
for every row under the shared protocol below. E01 includes completed L0 work;
its L1/L2 work remains pending.

| ID / priority | Action and target | Independent criterion and negative experiment |
| --- | --- | --- |
| E01 / P0 | Capability probe on GCC13/14/15 GDB and each profile ELF | Separate presence from operations; unavailable capability gives a reason without connection/injection |
| E02 / P0 | Typed int32/uint64/enum/float/struct/array/string reads | Boundary constants, 3.5, NaN/Inf, NUL/length, signedness; NULL/optimized-out/missing/unsupported must not become zero |
| E03 / P0 | Locals/arguments/backtrace snapshot, resume, read again | Consistent PC/function/type/stop ID; reject stale frames, restore temporary selection, distinguish shadowed locals |
| E04 / P0 | Read/write 1/2/4/8-byte RAM regions and a buffer | Byte oracle, outside canaries, endian; reject invalid ranges before access; retain failed write attempt and partial result |
| E05 / P0 | run_until function/file:line/address, two BPs on one PC | Actual breakpoint numbers/PC in StopRecord; ambiguity/missing/false/error conditions cannot succeed; retain external BPs |
| E06 / P0 | Scoped BPs, fault guards, budget exhaustion, scope exception | Own resources cleaned on PASS/FAIL/ERROR; guards retained, actual-location overflow/resume errors visible; normal boot after reset |
| E07 / P1 | stepi/step/next through call, branch and IRQ | Compare PC/instructions/frames with ELF; unexpected IRQ/fault is not expected step; prove no software/Flash BPs or reject operation |
| E08 / P1 | Finish natural int/void/uint64/struct calls; float separately | Return and side effects match natural path; explicit inline/unavailable/out_of_scope; verified hardware return point, no universal LR assumption |
| E09 / P1 | CPU write/read/access watchpoint on aligned RAM, same-value store | Distinguish changed-value/access semantics, PC/data; explicit hardware/width/scope/budget failure without software fallback |
| E10 / P1 | DMA writes RAM with a data watchpoint | Record triggering or lack thereof; sentinel IRQ/final BP bounds experiment, final buffer proves DMA; no stop does not mean no write |
| E11 / P1 | Capture natural GPIO/arithmetic calls: args/count/order | Predetermined calls and filtered arguments; extra/missing/reordered calls fail within a bounded window |
| E12 / P1 | Natural-call return/error/argument/output-buffer sequences | Independent caller postcondition, Nth-call trigger; explicit exhaustion/recursion/IRQ/callback errors; mutate only in post-stop dispatcher |
| E13 / P1 | Scoped RAM patch and GDB parameters, body exception | Restore own bytes/parameters for all outcomes; retain both original and teardown errors; no MMIO rollback claim |
| E14 / P1 | IRQ/Sleep frame walk and disassembly replacing TECH-008 internals | Correct exception, WFI and return; bounded attempts, unavailable unwind ERROR; no energy/timing claim |
| E15 / P2 | Direct pure-function and RAM-output calls in thread mode | Match natural call with same inputs; check SP/register context/canaries and RAM state separately; reject unsupported ABI/type without DWARF |
| E16 / P2 | Call interrupted by BP/fault or never completes | Preserve dummy frame and original cause; external timeout terminates GDB and invokes recovery, then positive boot; call+intercept separate |
| E17 / P2 | Run for bounded interval, interrupt, local/remote | Prove actual stop; preserve signal/disconnection/stuck-dispatch errors; GDB14 lacks interrupt, so design separately without worker GDB calls |
| E18 / P2 | RTOS threads, task selection, locals, thread-filtered BP | Only if server exports tasks, otherwise unsupported; IRQ is not a thread, restore selection; bare-metal single-thread success proves nothing about RTOS |
| E19 / P1 | masked/range/approx/sequence vectors, then bounded model replay | Independent vectors and deliberately wrong expectations yield correct FAIL; unique vector IDs, seed/action list, reset between sequences |
| E20 / P0 | Report/timeout/teardown with a large snapshot and serialization failure | Bound size, preserve the primary result on error, protect reserved keys; expected ERROR remains ERROR and a subsequent package does not delete earlier reports |

For stepping/finish/watchpoints, record actual insertion using GDB/server diagnostics
and, where available, remote-protocol evidence. Unchanged Flash readback alone does
not prove hardware-only operation. Never enable Flash breakpoints to make finish
succeed. Without evidence, mark that combination experimental/unsupported.

### Shared experiment protocol

1. Record experiment ID, module/fixture commit, MCU profile, GCC/GDB/Python,
   backend/version, flags, ELF/manifest SHA256, required capabilities and permitted
   interventions. Keep serial numbers and personal paths outside Git.
2. Build/collect/trace/prepare. Define oracle and expected failure before HW.
   Before writing, establish the agreed stand and original restore ELF/session.
3. Baseline boot/normal path, then one experiment. Bound the scenario by an external
   host timeout and predefined stop/byte/depth limits. CPU execution between stops
   is free-running, so wall time is not precise MCU time.
4. Save result.json, JUnit, GDB/server/recovery logs, actual StopRecord, inputs,
   outputs, mutation attempts and cleanup errors. Research statuses unsupported/not-run
   do not introduce runtime SKIP alongside PASS/FAIL/ERROR.
5. Remove owned resources, restore allowed RAM/parameters, reset_run and run an
   independent positive control. Finish the series with original firmware and
   boot/blink. Stop on failed restoration and retain ERROR.
6. After initial analysis, perform three predetermined positive repetitions per
   claimed combination. Never silently retry to obtain PASS; retain the first
   failure. Describe additional bounded IRQ attempts separately.

## 7. Work packages and rc3 admission criteria

| Package | Work | Output |
| --- | --- | --- |
| R0 — this research | Manual, code, external models, L0 probe | Plan/open decisions, no MCU |
| R1 | Fixture, StopRecord/ownership/record, typed snapshots, RAM | E01–06/E20 on F411; host failure tests and reproducible evidence |
| R2 | Steps/finish/watchpoints | E07–10 on M4/M3/M0; hardware-only and budget decisions |
| R3 | Capture/intercept/cleanup/vectors | E11–14/E19; migrate one HAL and one CMSIS scenario without `t.report` |
| R4 | Calls/async/RTOS | E15–18 separately; accept or defer without blocking R1–R3 |
| R5 | rc3 acceptance | Agreed matrix on final SHA, offline CI, independent consumer, recovery/restore |

Each package uses a new `codex/<task>` branch from the accepted base; branch chains
need a recorded order. Publication/land and tags belong to the owner. Prototype
helpers in the consumer fixture before promoting demonstrated mechanisms to core.
Public changes require a new specification revision, host failure regressions,
both API/migration documents, CHANGELOG and explicit API_VERSION/schema decisions.
Change the rc3 version when preparing the release, not merely its research.

Each admitted operation needs defined inputs/outputs/errors/ownership/limits,
compliance with threading and Flash policy, preserved JSON/original failures and
a normal path after intervention. Maintain an
`operation × MCU × GDB × backend × build mode → evidence/unsupported/not-run` table.
Not every cell must be supported, but the supported set and previous API regression
must be explicit.

Open decisions: P0/P1 scope; snapshot/StopRecord format; RAM/watchpoint budgets and
schema; permitted call/IRQ interventions; natural versus dummy-call interception;
final stand and restore project. Universal power-cycle, multiple-board orchestration
and code coverage remain separate tasks.

## Sources and reproducibility

The fixed primary source is the supplied PDF. Current HTML may change:
[Python API](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Python-API.html),
[breakpoints](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Breakpoints-In-Python.html),
[finish](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Finish-Breakpoints-in-Python.html),
[watchpoints](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Watchpoints.html),
[calls](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Calling.html).
Other primary sources are in section 4. External projects were neither installed
nor executed. This is an original plan, not a full Markdown transcription of the manual.

Original R0 limitations (subsequent experiments: [R1](RC3_API_R1.md)): no hardware proof on GCC14/15 GDB or
Linux; L0 does not test ABI, DWT/FPB, IRQ races or recovery. Existing TODO/STATUS/API
include historical statements, so the baseline was checked against code and
profile-specific evidence rather than summary counters alone.
