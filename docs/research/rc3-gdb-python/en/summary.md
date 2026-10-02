# GDB Python research summary: R1–R18

[Documentation](index.md) · [Русский](../ru/summary.md)

2026-10-02. Hardware experiments are paused by owner decision. RTOS and remaining
checks are recorded as [technical debt](technical-debt.md). API extension discussion
can proceed now without completing that queue. Core promotion requires separate
owner approval; this summary does not change the public API.

Each completed series has a separate report and result JSON. Reports retain initial
FAIL/ERROR outcomes and historical next steps; this summary and the debt register
define current status. The original manual/external approach review remains in the
[plan](plan.md); GDB14/16 capability probes are linked in the [index](index.md).

## Completed research register

| Report | Verified tools and finding | Evidence boundary |
| --- | --- | --- |
| [R1: data and state](r1.md) | Typed snapshots, frames, bounded RAM patch/restore, events and evidence recording | 48/48; consumer adapter, not public API; external termination needs separate recovery |
| [R2: navigation](r2.md) | Conditional/temporary points, ignore count, caller, C expressions, finish/return/call, disassembly | 56/56 HLA, 8/8 native DAP; initial HLA watch FAIL retained |
| [R3: actions and progress](r3.md) | Stop commands, command composition, unsigned deadline across wrap, C macros; watch differs from awatch | 32/32 native DAP; access and value change are distinct events |
| [R4: output parameters](r4.md) | Buffer and signed-status replacement, natural continuation and caller result | 32/32; separate ASM regression timed out with ERROR on native, HLA 4/4 |
| [R5: return types](r5.md) | uint64/float/struct through finish/call; scalar forced return | 64/64 positive; struct return FAIL; manual hidden-buffer technique 8/8 only on pinned ELF |
| [R6: stack and recursion](r6.md) | Caller/context filtering, selecting a recursive frame, finish/return | 24/24; function name does not identify a particular recursive frame |
| [R7: DWT ranges](r7.md) | Aligned watch ranges, splitting unaligned ranges, word-point budget | 16/16 + 8/8; rejected ranges remain unsupported; four word points, fifth rejected on this stand |
| [R8: FPB budget](r8.md) | Physical locations and finish headroom; freeing a point and resuming | HLA 16/16, native 8/8; six slots, four fault guards; not a universal MCU budget |
| [R9: interrupted call](r9.md) | DUMMY_FRAME, replacing a nested result and continuing | 16/16; register restoration does not roll back RAM or resume the original Python expression |
| [R10: fault/timeout](r10.md) | Fault classification, pre-call evidence, external recovery and control | 16 expected ERRORs and 16/16 controls PASS; finally after external kill is not guaranteed |
| [R11: IRQ](r11.md) | SysTick/TIM2, interrupted context and natural exception return | 16/16; basic MSP, not PSP/RTOS/extended FP frames |
| [R12: DMA](r12.md) | DMA changes buffer without watch stop; separate positive CPU controls | 16/16 native; no watch event does not prove no DMA write |
| [R13: WFI](r13.md) | Stop before WFI, IRQ wakeup, natural return and tick progress | 16/16; not energy, sleep duration or IRQ latency measurement |
| [R14: sequences](r14.md) | Errors/success, retaining accepted results, order and count of selected calls | 24/24; successive main-loop calls, not internal retry/backoff |
| [R15: optimization](r15.md) | O2/Os, inline frames, multiple locations, optimized_out and final sinks | 32/32; DWARF value availability does not prove the corresponding instruction executed |
| [R16: until/advance/nexti](r16.md) | Source lines, frame boundary, step interrupted by another point | 32/32; advance can finish before its target; out-of-scope differs from optimized_out |
| [R17: scalar ABI](r17.md) | void/double/float/six arguments, soft/hard ABI, finish/return/call and sinks | 48/48; hard ABI for double does not imply hardware double arithmetic |
| [R18: aggregates and C++](r18.md) | Small/Pair/HFA, this, const overloads and final sinks | 72 PASS, six FAILs: forced Pair soft/hard and HFA soft; Small and hard HFA pass |

Counts describe series and controls detailed in reports; adding them into an “API
support percentage” is invalid. PASS for an expected rejection does not make the
rejected operation supported. Main HW stand: F411CE, ST-Link, OpenOCD, Windows,
GDB14/16; HLA and native DAP differ. Linux host/prepare PASS is not Linux HW PASS.
Each report identifies exact ELF, builds, repeats and restoration.

## Conclusions for discussion

1. Typed observation, stop reasons, explicit point resources and bounded navigation
   form the strongest foundation. Failure contracts matter as much as convenient commands.
2. Result replacement needs caller verification and a natural control call.
   Current evidence does not support universal forced aggregate return.
3. MCU context, C/C++ frame and stop reason are separate entities. PC alone neither
   identifies an inline/recursive frame nor explains a stop.
4. Peripheral techniques need consumer profiles: halting the CPU does not make
   DMA/MMIO snapshots atomic, and watchpoints do not observe every memory writer.

Next: discuss [tool layers and API criteria](scenario-tools.md), the
[context proposal](execution-context.md), and select a first implementation scope.
This is a discussion proposal, not an approved rc3 scope or hardware resumption.
