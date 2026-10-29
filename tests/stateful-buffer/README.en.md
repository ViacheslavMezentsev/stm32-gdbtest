# Residual state and ring-buffer event ordering

[Documentation](../../docs/en/index.md) · [Русский](README.md)

Neutral TECH-021 example for **0.5.x / API 3**, with no board or peripheral models.
One C++ module runs on the host and on Cortex-M3 in Renode. The initialized POD object
contains no pointers; Python invokes real functions through `Target.call`, snapshots the
ELF-sized object and verifies complete restoration even after FAIL. This is educational
firmware, not test hooks added to a consumer application.

## Assertions

| Scenario | Intervention and independent expectation |
| --- | --- |
| HW_EMU_NEXT_COMPLETE | Length-3 packet followed by length-2 without reset: two publications, exact second payload |
| HW_EMU_NEXT_TIMEOUT | Partial packet, expire, new packet: one publication with no stale tail |
| HW_EMU_RING_ORDER | Ring wrap, RX error during TX, kick before/after complete, repeated complete: exact output; new enqueue must not enlarge an in-flight segment |

Host additionally checks full-queue refusal. Timeout is an expire event, not elapsed-time
measurement; complete is an explicit event, not real IRQ/DMA. Selected ordering does not
establish freedom from all races, memory-barrier correctness or RTOS safety. The ring has
one owner; physical transmission and CRC are not modeled.

## Reproduce

From repository root, with g++ on PATH:

```powershell
python tests/stateful-buffer/run.py --host-only
python tests/stateful-buffer/run.py --toolchain "$HOME/xpack-arm-none-eabi-gcc-14.2.1-1.1" --renode "C:/Program Files/Renode/renode.exe"
```

Linux with the same tools installed:

```bash
python3 tests/stateful-buffer/run.py --toolchain /opt/xpack-arm-none-eabi-gcc-14.2.1-1.1 --renode /opt/renode-1.17.0/renode
```

`--host-cxx` selects the host compiler. Requires Python 3.11+, GDB with Python, ARM GCC and
Renode 1.17. On Windows Docker keep source and build in one volume following
[local CI](../../docs/guides/en/local-ci.md). The runner owns Renode and never attaches to an
existing endpoint; see the [backend](../../docs/guides/en/RENODE.md) for its listening-port limitation.

## Red control, fix and repeat

`DEFECT=1` retains used after a complete packet/expire; `DEFECT=2` lets kick modify an
in-flight segment; `DEFECT=0` is corrected. Host runs all three variants. Renode runs the
same three scenarios on variants 1, 2, 0, 0: **12 expected outcomes**, including 3 intentional
FAILs. Success requires the exact scenario inventory, expected failed-check name, saved
capture, verified object restoration and cleanup VERIFIED. Raw FAIL is not rewritten as
PASS; summary PASS means agreement with the expected matrix.

`build/stateful-buffer/<id>` retains input snapshots and SHA-256, build/version logs, ELF,
each scenario's result/records and summary.json. The command returns 0 for a matching
matrix, otherwise 1 with retained ERROR/FAIL. An interrupted campaign is not PASS.
Repeating the corrected variant checks reproducibility and owned-process cleanup.
Restoration concerns only the model object; emulator destruction does not prove MCU recovery.

## Transfer

Replace educational expectations with project requirements and establish ownership of objects,
callbacks and buffers. Add real registers only through MMIO/SVD and separate stand admission.
Establish original FAIL, then the fix and neighboring cases using the same scenario.
[Technique](../../docs/en/TESTING_TECHNIQUES.md#tech-021), [DDTT](../../docs/en/DDTT.md#consumer-feedback).

Verified 2026-10-27: Windows/Linux host, Renode 1.17 Windows/Linux with xPack GCC/GDB 14.2.1 / 15.2.90. Each OS: 12/12 expected outcomes, 3 intentional FAILs, saved capture and object restoration. This is not hardware acceptance.
