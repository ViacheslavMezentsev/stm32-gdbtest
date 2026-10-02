# GDB Python API research for rc3

[Documentation](../../../en/index.md) · [Русский](../ru/index.md)

One research project lives here: the original plan, series reports and sanitized
results. Research is ongoing; reports retain the state of individual experiments,
including FAIL/ERROR. This is not an approved public API extension.

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

[Consumer](../../../../tests/api-experiments/CMakeLists.txt) · [GDB probe](../../../../tools/research/gdb_api_probe.py)
