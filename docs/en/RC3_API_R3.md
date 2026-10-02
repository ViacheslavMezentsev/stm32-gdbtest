# rc3 R3: stop actions and progress counters

[Documentation](index.md) · [Русский](../ru/RC3_API_R3.md)

2026-10-02. Continuation of [R2](RC3_API_R2.md) on `codex/rc3-api-r1` after
`33938d2`. Experimental consumer only; core promotion requires explicit owner
approval. Public API, specification and package version are unchanged.

## Verified techniques

The starting examples were the user's `test_runner.cmd` and `.gdbinit.txt` from
buck-boost-course. They were read, not executed. Their `cmds` splits text on `;`,
and `break ...; continue; finish` waits for a natural function call.
This differs from invoking a function directly through the GDB evaluator.

| Scenario | Result and application |
| --- | --- |
| COMMANDS | A conditional hardware breakpoint on `sum_bytes` executes `return 100; continue` as a GDB command list. A separate sentinel stop confirms the changed caller checksum. After removing interception, the next call computes normally. This supplies a chosen result to existing handling code without a firmware hook |
| DEADLINE | A hardware watchpoint on `(unsigned int)(cycles - $start) >= 3` stops after three completed application cycles. Starts0 and `0xfffffffe` cover wraparound. This bounds waiting by completed operations |
| SAMEVALUE | Repeating the computation with argument0 stores the previous checksum. `watch` reports no stop; a sentinel proves cycle completion. `awatch` reports access before cycles increments. This distinguishes a value change from an access |
| LANGUAGE | `macro define`, `sizeof(input->bytes)` in the current C frame, and a parameterized `define` command with `if/else` work. A list of complete Python strings preserves `;` inside `printf`; a command error stops the sequence before the next action |

Code: [scenarios](../../tests/api-experiments/profile/tests/board/test_automation.py),
[command composition](../../tests/api-experiments/lab/commands.py).

## Technique refinements

- A breakpoint command list ends when execution resumes: commands after `continue`
  are skipped. A separate `$after_continue` remaining0 verifies this. Check the
  result after control returns to Python at the verified sentinel. This is a CLI
  breakpoint command list, not inferior state modification from `Breakpoint.stop()`.
- `return` discards the current frame; a subsequent `finish` applies to its caller.
  Intercepting watchdog initialization can prevent normal initialization but does
  not prove that an already running watchdog is disabled. R3 did not test watchdogs.
- A progress counter cannot replace an external timeout: a hang without changes
  to `cycles` cannot trigger this watchpoint. For `uwTick`, separately establish
  its source, units, IRQ operation and halt behavior. Modular subtraction handles
  the tested single wrap; it cannot recover an arbitrary number of full wraps.
- RSP records six `T05watch` packets for two trials of three increments: GDB
  hides intermediate hardware stops while the predicate is false. A same-value
  checksum store also produces `T05watch`, but GDB continues to the sentinel.
  Filtering does not eliminate core halts or debugger effects on execution timing.
- `awatch` catches reads and writes. Proving a write requires instruction context
  and control points. Here firmware assigns checksum and does not read it in the
  observed section. This observation covers CPU accesses, not DMA.
- `execute_sequence` runs trusted commands in order and propagates errors.
  It is not a transaction: earlier effects remain. It does not automatically
  validate the stop reason; check the expected breakpoint after `continue`.
  Unlike `split(';')`, it takes complete command strings in a list.
- The macro is defined by the GDB scenario. This does not test importing all header
  macros from DWARF or provide a full C compiler; expressions depend on the frame.

Semantics: [GDB breakpoint command lists](https://www.sourceware.org/gdb/current/onlinedocs/gdb.html/Break-Commands.html),
[watchpoints](https://www.sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Watchpoints.html),
[forced return](https://www.sourceware.org/gdb/current/onlinedocs/gdb.html/Returning.html).

## Stand, evidence and reproduction

F411CE, ST-Link V2J43M28, SWD1MHz, OpenOCD0.12.0 native DAP/SWD, Windows.
The same GCC13 ELF (`-Og -g3 -fno-lto`, soft-float):
`38375f4f7d58cdb637c69ae099b47c03061230a9df4eecd530475cbc96a2fd19`.
No new firmware code or hooks.

Add `--suite r3 --native-stlink` to the [R1 command](RC3_API_R1.md#reproduction);
two `--gdb` arguments select GDB14 and GDB16. Without `--execute`, only preparation
runs. Four scenarios run once plus three predetermined repeats on each GDB.

Results: **32/32 HW PASS** (16 on GDB14/Python3.11,16 on GDB16/Python3.13).
Baseline and subsequent restoration: HW_BOOT/HW_GPIO PASS, reset_run;
restore ELF `1ff37ae10a007401de5e0eaf826764f60a2849c8b7821c123f12caa28c2e79c3`.
The [sanitized summary](../research/rc3-r3-results.json) records versions, hashes,
checks and events. Full logs remain locally under
`tests/api-experiments/build/evidence/20261002T003408.255257Z/`.

Windows/Linux build and host CTest: **20/20 PASS** (18 prepare, traceability,
20 host regressions grouped into one test). The earlier overall format FAIL from
R1 remains unresolved. Linux HW, other boards/servers and HLA for R3 were not tested.

Next: DWT width/alignment and budget; stack filtering with recursion; output
buffers, return ABIs and interrupted direct calls. These items imply neither
hardware validation nor approval of a new public API.
