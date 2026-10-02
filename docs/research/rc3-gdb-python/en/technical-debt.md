# rc3 GDB Python research technical debt

[Documentation](index.md) · [Русский](../ru/technical-debt.md)

2026-10-02: owner decision **pauses RTOS and all remaining hardware experiments**.
This is the whole R1–R18 research debt register, not an automatic next-run plan.
Resumption requires a separate owner instruction and confirmation of current stand
and restoration firmware. No deadlines. No item below is completed or HW verified.

Priorities express dependencies of future promises, not work authorization:
**A** before promising the corresponding API; **B** before extending coverage;
**C** separate research. Until closed, an explicitly limited contract may exclude
the unverified capability.

| ID / priority | Debt and evidence | Closure criterion after resumption |
| --- | --- | --- |
| D1 / B | RTOS: tasks, PSP, context switch, filters; queue stage 9, R11 only basic MSP | Ordinary RTOS firmware without hooks; current/interrupted task identity, stack switching, locals, filters and natural continuation; record RTOS/port/build |
| D2 / A | Composition reliability: shared address, foreign points, predicate errors, scope, settings, call budget, bounded replay; stage 10 | Separate positive/rejection scenarios, ownership/restoration, both errors on cleanup failure, no false target arrival or unbounded waits |
| D3 / B | Portability: stage 11 F030/F103, other backends/OS; main R1–R18 on F411/Windows | Confirm actual wiring; select representative cases and record MCU/GDB/backend/ABI; HW and restore on each claimed combination. Linux prepare is not HW |
| D4 / A | General execution context: [proposal](execution-context.md), R1 epoch does not track all writes without continue | Verify required fields, selected vs physical frame, mutation/reset/reconnect revision, unavailable states, immutable/serializable snapshots, limits and no implicit MMIO |
| D5 / A | Forced aggregate return: R5, R18 Pair soft/hard and HFA soft FAIL; pinned sret workaround narrow | Explicitly exclude ABI forms or prove caller result delivery and natural control for each supported ABI/ELF; never hide FAIL with fallback |
| D6 / A | Backend-specific stops: HLA watch R2 and native stepi timeout R4 | Isolate differences, obtain repeatable navigation/watch controls, retain original ERROR/FAIL and define supported backend per operation |
| D7 / A | Resources: R7 DWT ranges/four-word budget, R8 FPB6 and finish reserve | Verify combinations/overlaps/expressions, physical locations, foreign and internal call/finish points; rejection before/during insertion without resource leaks |
| D8 / B | IRQ/FPU: PSP, nested IRQs, extended frame/lazy stacking; R11/R17 partial | Prove correct interrupted context and natural exception return preserving claimed FP/stack state; scalar ABI PASS is insufficient |
| D9 / B | C++ and types: virtual/inheritance, constructors/destructors, lifetime, exceptions/RTTI, variadic, nontrivial aggregates, special floats | Separate requested capability/rejection matrix on ordinary firmware; do not generalize R18 const-overload results to all C++ |
| D10 / B | Navigation/optimization: bare until, further recursion/inline/LTO cases and vanished functions | Verify actual stop reason, ambiguous locations and value availability without depending on one DWARF layout |
| D11 / B | Peripherals/time: R12 DMA invisible to watch, R13 does not measure sleep; MMIO read effects and no full rollback | Define observable signals, read/halt effects and external measurement where needed for a concrete contract; no global atomicity/timing claims |
| D12 / B | Application behavior: R14 successive calls, not actual retry/backoff | Separate ordinary implementation of required retry/deadline, final sinks, order, attempt bounds and natural control |
| D13 / C | Universal power-cycle, multiple-board orchestration, code coverage | Separate research with boundaries, stand and acceptance criteria; not automatically part of rc3 |

Open D2/D4–D7 need discussion before adding corresponding API promises. Exclusions
can be documented now; new measurements are paused. Each future closure needs a
separate RU/EN report, anonymized results, build/stand description, retained failures
and restoration checks. Assign series numbers when work occurs; R19 is not reserved
for RTOS.

Current work is the [summary](summary.md), [classification](scenario-tools.md) and
contract discussion. Historical “next” statements in R1–R18/TODO/CHANGELOG do not
override this pause.
