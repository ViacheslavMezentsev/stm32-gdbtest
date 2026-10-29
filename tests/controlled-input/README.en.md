# Simulated input: write and ret

[Русский](README.md) · [TECH-004](../../docs/en/TESTING_TECHNIQUES.md#tech-004)

A5.1, release 0.6.0. The same neutral C++ source runs on host and Cortex-M3 in
Renode. No core changes, boards, GPIO, DMA, RTOS or instruments. Checkpoint functions
belong only to the educational workload; consumer firmware does not need test hooks.
Choose existing observation points in a real ELF.

## Independent expectations

Prerequisites → application → consumption → application branch → next input → restoration.
A successful write or forced return does not prove that the caller consumed it.

| Scenario | First iteration oracle | Outcome |
| --- | --- | --- |
| HW_INPUT_BASELINE | consumed=0, active=0, reads=1 | PASS |
| HW_INPUT_SRAM | Write 1 after refresh: consumed=1, active=1, reads=1 | PASS |
| HW_INPUT_RET_HIGH | Source 0, ret(1): consumed=1, active=1, reads=0 | PASS |
| HW_INPUT_RET_LOW | Source 1, ret(0): consumed=0, active=0, reads=0 | PASS |
| HW_INPUT_TOO_EARLY | Write 1 before refresh; consumed=0 contradicts the desired 1 | intentional FAIL |
| HW_INPUT_EXCEPTION | SRAM change, then a specific Python exception before consumption | intentional ERROR |

Positive substitutions also check the following ordinary zero input and counters.
ret skips the producer's body; its source is deliberately opposite to the forced
value. The caller has not processed the value immediately after ret. Continue to
after_processing before checking consumption. ret is not awaited; navigation in
async def is. Recheck frame/side-effect timing when changing ELF, optimization or LTO.

All mutable state is one 32-byte POD including guards and counters. Address/size
come from ELF. finally restores and compares every byte, recording before/after
SHA-256 even on FAIL/ERROR. This restores data, not PC/stack history. Backend cleanup
is separate. GDB process loss, power failure, DMA/IRQ and external resources are not covered.

## Run

```text
python tests/controlled-input/run.py --host-only
python tests/controlled-input/run.py --toolchain <GCC-root> --renode <Renode-executable>
```

Same command on Windows/Linux; requires host g++, ARM GCC/GDB with Python and Renode
1.17. Host checks the processing model, not actual GDB ret. Renode uses the real runner.
Each scenario starts a fresh ELF session. Two rounds produce 8 PASS, 2 expected FAIL
and 2 expected ERROR. build/controlled-input/<UTC>/ holds inputs/hashes, ELF, tool
versions, command logs, raw result/records and summary.json.

The analyzer uses common result/records readers, checks integrity/completeness,
exact negative outcomes, independent numeric expectations and restoration. Raw
FAIL/ERROR are never rewritten. Campaign PASS means the expected matrix matched,
not that all scenarios passed. Missing/truncated data or unrelated errors are refused.

## DDTT boundary

Evidence covers software-input handling, not electrical signals, wiring, switches
or peripheral acquisition. No timing claim. observation records the method, supplied
value, consumed/active/reads/cycles and excluded layers. This is an example convention,
not a new runner schema.
