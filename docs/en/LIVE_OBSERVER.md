# Neutral VTOR/FPB example

[Documentation](index.md) · [Live execution](LIVE_EXECUTION.md) · [Русский](../ru/LIVE_OBSERVER.md)

[Sources and commands](../../tests/live-observer/README.en.md) demonstrate API 3 without
new Target methods. The first experiment needs only Renode, not a board. Sources are
published; binaries, logs, snapshots and personal stand settings stay in build.

## Observations

The neutral ELF executes `original_work(x) = x * 3 + 1` and counts calls and acknowledged
IRQ0 events. Python independently computes the sum: seven calls produce 70. A pending
bit is not a queue: each software IRQ is acknowledged before the next one is issued.

The linker reserves 4096 bytes at 0x20008000; the stack is below 0x20007000. The first
1024 bytes hold code and the remap table (+0x300), counters are at +0x400 and the
512-byte vector table at +0x800. Guard bytes separate the regions. Sizes/addresses
are checked against the ELF and the complete region is saved before mutation.

| Case | Expected outcome |
| --- | --- |
| BASELINE | Seven original calls/IRQs, sum 70 without an observer |
| SEVEN / ZERO | Seven observed entries / valid zero in a completed window |
| EXCEPTION | Intentional ERROR before resume; cleanup VERIFIED |
| HALT | Passive timeout followed by explicit halt and assessment |
| ACTIVE | Intentional ERROR inside the known ISR; bounded drain and cleanup |
| NEGATIVE | Intentional FAIL: expected eight, observed seven |
| TRAMPOLINE | Direct SRAM call replaying the displaced prologue |
| FPB_ZERO / FPB_SEVEN / COMBINED / FPB_EXCEPTION | Qualified F411 only: remap, combined VTOR, failure after installation |

Successful removal is followed by three original calls without reset. Scenario,
observer cleanup and external recovery have separate evidence. Missing records
cannot be interpreted as zero events or successful cleanup.

## Mechanism boundaries

The VTOR wrapper preserves arguments and EXC_RETURN and branches to the original ISR.
FPB uses code COMP5 and literal COMP7 with the checked F411 geometry. The trampoline
replays only `push {r7}; sub sp,#12`, then branches to entry+4. A changed prologue,
ABI or layout requires a new decision, not disabling validation.

This Renode platform does not implement remap: four cases are listed as NOT_SUPPORTED.
A direct trampoline call tests instructions and results, not FPB. The Cortex-M3 model
exercises instructions shared with Cortex-M4 soft ABI; it does not emulate all F411
peripherals. RTOS, DMA, physical timers, nested IRQs and timing transparency are not
proven. The wrapper changes execution time and flags; it is not a universal arbitrary
instruction or function replacement.

Low-level helpers use GDB-Python on the main thread and direct accesses to selected
core registers. This is a separately qualified procedure, **not the Target.mmio
transport guarantee**. For new peripherals use SVD/MMIO and [model plus board
verification](MMIO.md). Raw GDB is not a general way to bypass async API restrictions.
Ordinary data reads remain synchronous; navigation inside async functions requires
await, and waiting for a stop does not stop the target itself.

## Hardware route: separate admission only

No board is run during this transfer. The research F411 pilot on API 3 produced
12/12 expected outcomes and independently verified Flash/SRAM and saved registers.
This is the example's provenance, not fresh hardware acceptance of the published commit.

1. Confirm the particular free F411CE/ST-Link/OpenOCD, disconnected loads, watchdog
   state and permission to reset/resume. Check reset-halt state before backup.
2. `prepare.py --toolchain <root> --out <new-build-directory>` builds the package;
   `campaign.py --package <directory> --stand <local.toml> --serial <serial>` prints a plan.
3. After actual admission, write a local admission JSON with `serial`, `elf_sha256`,
   `stand_free`, `watchdog_inactive`, `loads_disconnected`, `reset_resume_allowed`.
   The last four values must be true; the file records the operator's decision,
   rather than automatically proving electrical conditions.
4. Add `--allow-hardware f411ce --admission <file>`. Identity, Flash size and erase
   geometry are checked; fresh Flash/SRAM are read twice. Backup does not repeat
   reset between snapshots. Only the selected ELF in the first sector is programmed.
5. Scenarios use verify-only. An unexpected outcome stops the campaign; external
   recovery runs in finally. FPB is removed only after proving ownership from the
   journal and current state. Ambiguity blocks further writes.
6. Restore the first sector, verify all Flash, then restore and verify SRAM.
   Confirm CPU reset-state and independently compare saved FPB/VTOR/NVIC through
   a new connection without reset/resume. Automatic recovery checks memory and
   PC/SP/xPSR/PRIMASK; independent system-register comparison remains a mandatory
   operator check. Not all peripheral registers or the previous live context are restored.

After loss of GDB, use the same `campaign.py` with `--recover <fresh-backup>` and
`--events <same-attempt/fpb-events.jsonl>`, the original package/stand/serial/admission
and explicit allow-hardware. Do not mix attempts. Stop on unusable backups, USB failure
or ambiguous ownership; recovery cannot be promised while the device is inaccessible.
The board remains halted; the original application does not automatically resume.
Do not use mass erase.

## Techniques from application scenarios and migration

These are generalized techniques from protocol, power, measurement and telemetry
scenarios. Application bridge logic and laboratory supply control are not copied.

| Technique | API 3 application |
| --- | --- |
| Qualify the rig before testing behavior | Check memory/IRQ ownership, complete snapshot and layout; mismatch aborts before mutation |
| C++ `this` and DWARF context | `await t.reach(...)`, obtain type/size/address in a stopped frame; do not retain a lazy gdb.Value to read after resume |
| Independent oracle | Calculate expected bytes/sum on the host; compare original and observed counters |
| Separate object and peripheral snapshots | RAM restores byte-for-byte; registers need their own ordering, permissions and side effects |
| Observe → records → checks | Save JSON-compatible facts before a check can interrupt the scenario; require series completeness |
| Event order and sample freshness | Conditional breakpoints, publication counter/firmware tick, bounds on stops and elapsed time; host time is not MCU time |
| Repeat after cleanup | Repeat the original route without reset; a successful main verdict must not hide recovery errors |

Old `execute("call ...")` is not migrated into async scenarios. For a **simple function
name and numeric arguments**, use `await t.call(...)`. The call interface does not
accept `this->method`, `Class::method`, pointer strings or arbitrary expressions.
Successful C++ preflight does not change this. Exercise methods through normal firmware
flow and navigation; a separate raw-GDB experiment has its own limitations and is not
presented as the API. Replace hidden `HAL_GetTick()`/`getData()` inside read/evaluate
with accessible data reads or a separate supported call whose saved result is used later.
Replace old execute-based MMIO writes with explicit SVD/MMIO operations; do not mechanically
read-modify-write W1C/read-clear registers. Table check evaluates expressions; a scalar
check compares already obtained Python values. Strings in records are not evaluated.

## DDTT

An entry counter is event evidence; a sum is result evidence; recovery is evidence that
the experiment remains usable. The map author separately approves which expectations
relate to which source lines. Use the [DDTT exporter](DDTT_COVERAGE.md), preserving the
environment and source revision. Do not merge hardware and emulator observations into
an unlabelled counter. This example does not generate invented line coverage.

The run also creates `map.json`, `build-manifest.json`, `view/lcov.info` and
`view/ddtt-evidence.json`. Three reviewed links in `map.template.json`: `calls++`
to the original call count, `return x * 3 + 1` to the independent sum, and `delivered++`
to the acknowledged IRQ count. These are expectations linked to lines, not an instruction
trace. The negative scenario tests failure detection and is deliberately excluded from
the firmware behavior map. Select this run's absolute `view/lcov.info` in Coverage Gutters.
The manifest describes explicit single-source compilation; it does not claim a Ninja
dependency graph or hash all installed toolchain headers/binaries.
