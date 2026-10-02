# GDB Python API research for rc3

[Documentation](../../../en/index.md) · [Русский](../ru/index.md)

One research project lives here: the original plan, series reports and sanitized
results. Hardware experiments paused on 2026-10-02; reports retain individual experiments,
including FAIL/ERROR. This is not an approved public API extension.

- [API scope proposal](api-proposal.md) — operations, contracts, implementation packages and open questions.
- [R1–R18 summary](summary.md) — all reports, findings and evidence boundaries.
- [API, techniques and patterns](scenario-tools.md) — application areas, classification and API properties.
- [Named execution context](execution-context.md) — snapshot contract proposal.
- [Technical debt](technical-debt.md) — paused stages and open limitations.
- [Research plan](plan.md) — GDB Python manual review and experiment program.
- L0: [GDB14](../results/rc3-gdb14-capabilities.json), [GDB16](../results/rc3-gdb16-capabilities.json).

| Series | Report | Results |
| --- | --- | --- |
| R1 | [Typed data, frames, RAM and reports](r1.md) | [JSON](../results/rc3-r1-results.json) |
| R2 | [Navigation, calls, watchpoints and assembly](r2.md) | [JSON](../results/rc3-r2-results.json) |
| R3 | [Breakpoint commands, counters and same-value stores](r3.md) | [JSON](../results/rc3-r3-results.json) |
| R4 | [Output buffers and status substitution](r4.md) | [JSON](../results/rc3-r4-results.json) |
| R5 | [Return types and hidden struct result buffer](r5.md) | [JSON](../results/rc3-r5-results.json) |
| R6 | [Stack filtering and recursive frames](r6.md) | [JSON](../results/rc3-r6-results.json) |
| R7 | [Watchpoint ranges and budget](r7.md) | [JSON](../results/rc3-r7-results.json) |
| R8 | [Code breakpoint budget and finish headroom](r8.md) | [JSON](../results/rc3-r8-results.json) |
| R9 | [Interrupted calls and nested result substitution](r9.md) | [JSON](../results/rc3-r9-results.json) |
| R10 | [Fault and timeout of an unfinished call](r10.md) | [JSON](../results/rc3-r10-results.json) |
| R11 | [IRQ context and natural exception return](r11.md) | [JSON](../results/rc3-r11-results.json) |
| R12 | [DMA writes and watchpoint observations](r12.md) | [JSON](../results/rc3-r12-results.json) |
| R13 | [WFI, wakeup and delay progress](r13.md) | [JSON](../results/rc3-r13-results.json) |
| R14 | [Interception sequences and call order](r14.md) | [JSON](../results/rc3-r14-results.json) |
| R15 | [O2/Os, inline frames and value availability](r15.md) | [JSON](../results/rc3-r15-results.json) |
| R16 | [until, advance, nexti and stop reasons](r16.md) | [JSON](../results/rc3-r16-results.json) |
| R17 | [Scalar types and soft/hard-float ABIs](r17.md) | [JSON](../results/rc3-r17-results.json) |
| R18 | [Structures, HFA and C++ methods](r18.md) | [JSON](../results/rc3-r18-results.json) |

[Consumer](../../../../tests/api-experiments/CMakeLists.txt) · [GDB probe](../../../../tools/research/gdb_api_probe.py)
