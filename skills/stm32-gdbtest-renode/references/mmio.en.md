# MMIO: measure accesses, then validate on the target

[Русский](mmio.md). Resource for stm32-gdbtest-renode; resolve docs/tools/tests paths
below from the located module root, even when the skill was copied into another project.
Read docs/en/MMIO.md and docs/en/RENODE_PROBES.md before experimenting.

## 1. Preconditions and model

Choose one register/operation, expected read/write counts and effects from the MCU manual.
Record ELF and SHA-256, scenario, model, GDB/Renode versions and connection method.
Use a separate results directory and your own Renode process. The examples
`tests/renode-startup` and `tests/renode-cache` provide startup/ELF scaffolding, not a
universal MMIO model. Prepare and validate the required register model separately.

Log callbacks without additional GDB reads: event sequence, read/write, offset, width,
value and before/after state. Implement independent effects: WO logs any read, W1C clears
only one bits, read-to-clear returns the old value then clears, FIFO consumes an item.
Add a neighboring sentinel register to detect expanded accesses. A model error is not a
bus fault. RAM at a peripheral address is not a device model. Do not claim DMA support
unless implemented. Keep model initialization outside the measured window.

## 2. Measurement through real GDB

Use the GDB main thread, a real ELF and current Target methods. Reset the model before
each operation and place begin/end text markers in the GDB log. `set debug remote 1`
enables RSP diagnostics; disable it afterwards. Save `info mem` and cache policy.
Do not reset another session's memory map.

Compare counts at three layers: method, m/M/x/X packets, peripheral callbacks. Packet
count and buffer length do not prove transaction width. Investigate nocache/cache and
access-size 32 separately; caching may read neighbors or suppress repeated reads.
Exclude accesses from IDE watches and peripheral views while measuring.

Minimum matrix (isolated model only):

| Case | Reveals |
| --- | --- |
| Scalar versus structure/array read | access expansion to neighbors |
| write verify=True/False to WO | before read even with verification disabled |
| Ready mask versus reg OR mask for W1C | extra reads/RMW |
| Two explicit RTC/FIFO reads | count and order of destructive effects |
| Bitfield and moving LHS | hidden RMW and repeated path evaluation |
| 8/16/32, unaligned access | actual callback widths, not an API promise |
| Access denied by GDB memory region | refusal before model callback |
| Exception after access, short response | unknown effect, no automatic retry |

Validate the model itself against a known sequence first. Use a deliberately wrong
access-count expectation as a negative control: analysis must FAIL. Record scenario and
log-analysis verdicts separately. Missing/incomplete logs mean UNKNOWN/ERROR analysis,
not zero accesses. Label an injected exception after a real effect as injection, not
connection-loss testing. Do not hide retries to obtain PASS. Check cleanup and a fresh
launch afterwards; terminate only processes you own.

## 3. Transfer to a development board

Renode does not validate a specific GDB server or physical peripheral. Propose a minimal
hardware plan for the user's MCU: the same scenario segment, documented registers,
independent observable effect, permitted interventions and recovery. Confirm connected
loads and write authorization before experimenting; RTC/FIFO reads are interventions too.
Do not automatically transfer dangerous WO/unaligned negative cases to a board.
Do not use mass erase/option bytes or a generic snapshot of all registers.

Preserve authorized memory and verifiable initial state; account for DMA/RTOS and
peripherals while halted. WO/W1C/FIFO recovery is device-specific, not writing before.
Repeat the minimal positive experiment, verify recovery and retain FAIL/ERROR evidence.
Do not generalize to other backends/versions/MCUs without testing. Without a transaction
instrument, limit conclusions to observed effects, not an exact single-access claim.

Deliver expected/actual access tables, original logs and commands, separate conclusions
for module/GDB/model/board, unverified points and the next necessary experiment.
