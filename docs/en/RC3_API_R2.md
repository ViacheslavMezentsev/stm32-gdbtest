# rc3 R2: navigation, calls and stop recognition

[Documentation](index.md) · [Русский](../ru/RC3_API_R2.md)

2026-10-02. Experiments continue in `codex/rc3-api-r1`, after R1 commit `0d0db6a`.
**No promotion to core without explicit owner approval.** Public API,
specification0.58 and package version are unchanged. Code remains in the
[consumer](../../tests/api-experiments/profile/tests/board/test_navigation.py).

## Demonstrated results

Same WeAct BlackPill F411CE, STM32F411CEU6, ST-Link V2J43M28, SWD1MHz,
OpenOCD0.12.0, Windows. Both GDBs use the same GCC13.3.1 ELF (`-Og -g3 -fno-lto`,
soft-float), unchanged from [R1](RC3_API_R1.md):
`38375f4f7d58cdb637c69ae099b47c03061230a9df4eecd530475cbc96a2fd19`.

| OpenOCD interface | Scenarios | GDB14.2/Python3.11 | GDB16.3/Python3.13 |
| --- | --- | --- | --- |
| interface/stlink.cfg, HLA | CONDITION, HITCOUNT, RETURN, FINISH, STEP, CALL, ASM | 28/28 PASS | 28/28 PASS |
| interface/stlink.cfg, HLA | WATCH | FAIL: watchpoint identity absent | FAIL: same limitation |
| interface/stlink-dap.cfg, dapdirect_swd | WATCH: write/read/access | 4/4 PASS | 4/4 PASS |

This means **56/56 navigation runs** and **8/8 watchpoint runs on different interface
variants**, not all eight scenarios on each interface. Successful sets contain an
initial run and three predetermined repeats. Each WATCH run tests three access types sequentially.

Every series restored ELF
`1ff37ae10a007401de5e0eaf826764f60a2849c8b7821c123f12caa28c2e79c3`,
passed HW_BOOT/HW_GPIO and left reset_run. GPIO checks the PC13 register, not light.
F030/F103/F401, other servers, Linux hardware and other ABIs were not tested.

## Techniques demonstrated on this stand

| Technique | Experiment and useful behavior |
| --- | --- |
| Select a particular invocation | Temporary hardware BP with `sequence == 3 && input->mode == MODE_ACTIVE`; recheck condition after stop and confirm deletion. Select state without a firmware hook |
| Skip warm-up | ignore_count2 stops the third natural call, sequence2 and hit_count3; separate startup from steady operation |
| Recognize a stop by context | Current function, caller at depth1/2 and arguments; built-in `$_caller_is("process_sample")` is available on both GDBs and agrees with frame walking; reject wrong name/depth |
| C context inside Python | Evaluate source expressions `sequence + (uint32_t) input->mode` and `sizeof(input->bytes)` in the frame; use $result to bridge Python and GDB. This is trusted evaluation, not a read-only sandbox |
| Replace a natural call result | `return 100` from sum_bytes; independently verify caller checksum using100 instead of773. Explore result-handling paths without changing firmware |
| Observe the actual result | FinishBreakpoint completes natural sum_bytes, captures773 and selects process_sample; verify subsequent checksum. Distinct from forced return |
| Choose navigation granularity | stepi advances PC; bounded step enters sum_bytes; CLI finish returns; next passes calls without selecting child frames |
| Use an existing function as a calculator | Direct `sum_bytes(sample.bytes, 8, 5)` returns775, preserving PC/SP and input RAM. Proven only for this pure uint32 function in thread mode |
| Locate data publication | Native DAP write-watchpoint stops the first cycles increment to1; array read/access points stop in sum_bytes with expected identities |
| Recognize a terminal handler | Jump to existing Default_Handler, identify b.n to itself via disassembly and0xE7FE, confirm fixed PC across three stepi; reset to main after deliberately abandoning normal flow |

Compare branch addresses **numerically**, not by matching hex(pc) strings.
The [pure helper](../../tests/api-experiments/lab/navigation.py) checks b/b.n/b.w
and its numerical target. Host regressions reject conditional bne, bl, another
target, missing address and invalid caller depth. Encoding0xE7FE applies only to
this 16-bit Thumb self-branch, not arbitrary infinite loops or a system-wide hang.

A useful composition for future experiments: select a call by arguments/stack →
capture inputs → replace its result → continue to publication → compare with an
independent oracle. Components were demonstrated; a universal interception
dispatcher or arbitrary control-flow replacement was not.

## Why HLA watchpoints failed

GDB14 passed five scenarios before WATCH failed. OpenOCD registered a DWT0 write
watchpoint on cycles, but returned T05 without watch:<address>; the Python event
lacked the expected point number. An isolated GDB16 run reproduced this. Both
original FAIL reports and successful restoration remain recorded. Replacing
expected-point identification with merely noticing a stop would conceal the defect.

The controlled comparison changed only the OpenOCD ST-Link driver to stlink-dap.cfg,
with explicit dapdirect_swd transport. On the same MCU/probe/speed/ELF, the server
returned T05watch:..., T05rwatch:... and T05awatch:..., and GDB produced expected
breakpoint events. Logs contain Z2/Z3/Z4 packets.

The --native-stlink flag exists **only in the experimental runner**.
A [local transform](../../tests/api-experiments/lab/openocd_native.py) temporarily
replaces command construction in that Python process, preserving serial/target/speed.
Core files, TOML schema and installed OpenOCD were not changed. A host test checks
argument preservation and rejection of unexpected input commands. Native DAP is
not claimed as a supported production backend configuration.

## Internal next/finish/call breakpoints

The scenario sets `monitor gdb_breakpoint_override hard`, enables auto-hw and
disables displaced stepping. GDB/OpenOCD diagnostics begin after ELF loading.
The summary records Z0/Z1 requests and hardware/software additions for the successful
navigation series. **No Z0 or software additions occurred in the measured part**;
FINISH/STEP/CALL used Z1 with hardware insertion confirmed. This is stronger evidence
than unchanged Flash readback alone.

Configuration basis: [GDB auto-hw](https://www.sourceware.org/gdb/current/onlinedocs/gdb.html/Set-Breaks.html)
selects hardware for read-only addresses; [OpenOCD override](https://openocd.org/doc-release/html/Server-Configuration.html)
forces hardware insertion. Do not generalize this protocol to another server.
FPB exhaustion must remain an error, never permission for software fallback.

## Reproduction and evidence

The [sanitized summary](../research/rc3-r2-results.json) includes stages, versions,
source hashes, events, outcomes and protocol counters. Full logs remain under
tests/api-experiments/build/evidence/:

- 20261001T235131.910896Z: initial HLA series, WATCH FAIL on GDB14;
- 20261001T235327.668203Z: isolated WATCH FAIL on GDB16;
- 20261001T235455.208709Z: seven navigation scenarios,56/56;
- 20261001T235712.923348Z: native DAP WATCH,8/8.

Names use UTC; local date was2026-10-02. Earlier reports were not overwritten.
The protocol summary becomes ERROR on an unexpected scenario FAIL; the original
result.json stays FAIL. All four summaries record restored=true.

Add --suite r2 to the [R1 command](RC3_API_R1.md#reproduction). For navigation,
list the seven --test HW_R2_... identifiers above, excluding WATCH. For data-point
comparison use `--test HW_R2_WATCH --native-stlink`. --execute still enables HW;
otherwise preparation only. Specify one --gdb per GDB version. Changes to the
physical stand require separate agreement.

Windows and Linux build/host/prepare: **16/16 PASS** (14 prepare, traceability and
17 host regressions grouped in one CTest). No new C code. The old overall format
failure documented by R1 remains unresolved and is not reported as PASS.

## Remaining limits

Same-value store watch/awatch differences, DMA, DWT width/alignment/exhaustion,
C-condition errors, recursion, IRQ and RTOS are untested. There is no void/float/
structure/64-bit return matrix, out_of_scope or side-effecting-call coverage.
A successful direct call does not prove recovery from a hung dummy frame.
nexti/until/advance, arbitrary safe intra-function jumps, macros from new consumers
and live-code patching remain untested. All GDB APIs ran on its main thread.

Next experiments: same-value writes/watchpoint limits, stack/argument call filters,
result branches/output buffers, additional ABIs and interrupted calls. These results
expand the experimental set; **they do not authorize promotion to core**.
