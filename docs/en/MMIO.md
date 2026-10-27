# MMIO: peripheral registers and API boundaries

[Documentation](index.md) · [Русский](../ru/MMIO.md)

**Known limitation: the existing general memory methods are not an MMIO interface
without hidden accesses.** 0.5.x provides a separate [mmio interface](api/mmio.md). The warnings below about general methods still apply.

## What scenario authors need to know

| Path | Behavior and risk |
| --- | --- |
| `read`, `evaluate` | Expression evaluation and value conversion may access memory. Structures/arrays may touch neighboring registers; `volatile` does not guarantee one read. |
| `check(rows)` | String actual and expected cells are evaluated; both sides may read peripherals. |
| `check(name, actual, expected)` | Ready Python values are compared without MCU reads; evaluating the arguments may already have read the MCU. |
| `write`, including `verify=False` | The before read remains. MMIO outside scope has no confirming readback, but disabling verify does not remove before. This is not a universal safe write for WO/read-to-clear/FIFO. |
| `write` with expressions/bitfields | Single RHS evaluation in API 3 does not remove before, repeated LHS evaluation, or possible GDB read-modify-write for bitfields. |
| `memory` | Access is restricted to SRAM/Flash windows; peripherals outside those windows are rejected. Do not declare MMIO as ordinary profile memory to bypass validation. |

RO means read-only, WO write-only, W1C clears a bit by writing one, and read-to-clear
clears on reading. FIFO reads may consume an item each time. A snapshot followed by
writing the old value is not a recovery procedure for these registers. IDE peripheral
views, watches and automatic refresh can issue accesses independently of the scenario.
Halting the core does not stop DMA or peripherals.

Do not substitute zero for unknown state. An access may have taken effect before an
error; do not retry automatically. Do not verify an outcome through a destructive read.
Choose an independent safe observation from the specific device documentation.

## Guarantee boundary

Predictable request count and order **inside the module before handing off to the
transport** are the goal of a separate MMIO contract: explicit width/permissions,
validation before access, no before/readback/RMW/retry, and unknown effects after errors.
This is work in progress, not a promise of an implemented method. The table applies
until that contract is accepted.

One GDB call does not prove one bus transaction. `volatile` is a language/compiler type
property; it does not describe WO/W1C/FIFO or prohibit reads in the scenario wrapper.

GDB provides [memory region attributes](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Memory-Region-Attributes.html):
`ro/wo/rw`, access size and `nocache`. However, [RSP m](https://sourceware.org/gdb/current/onlinedocs/gdb.html/Packets.html)
does not require a particular access size/alignment from the server and may be unsuitable
for MMIO. The `32` attribute alone does not establish a physical 32-bit transaction through
Python memory API and the selected server. Caching may suppress reads or expand them to
neighboring addresses. Preserve and restore the original GDB settings during experiments.

## Recommended route: model, then the target board

Use [stm32-gdbtest-renode](../../skills/stm32-gdbtest-renode/SKILL.md) and its
[MMIO resource](../../skills/stm32-gdbtest-renode/references/mmio.en.md).

1. **Renode:** model register effects, not RAM at a register address. Correlate API calls,
   GDB/RSP requests and model callbacks: direction, address, width, count, order and
   effect. Check WO, W1C, read-to-clear/FIFO, a negative control, and errors after effects.
   A wrapper-injected error is not a real bus fault.
2. **Your target board:** after authorizing effects, repeat the same minimal scenario
   segment with the specific ELF, MCU, probe, GDB and server. Define safe observation and
   recovery based on device semantics beforehand. Preserve initial FAIL/ERROR results.
   Repeat affected checks when changing the backend or its version.

These stages provide evidence at different layers; Renode PASS does not replace hardware
validation, and the final register value on a board does not prove physical transaction
count. Mark unsupported peripherals and unmeasured boundaries as unverified.


Hardware acceptance on 2026-10-16: six MCUs, 141 assertions for the selected 32-bit GPIO/DMA route, recovery VERIFIED. Scope and matrix: [API_ACCEPTANCE](API_ACCEPTANCE.md).
