# rc3 R4: output buffers and return substitution

[Documentation](index.md) · [Русский](../ru/RC3_API_R4.md)

2026-10-02. Continuation of [R3](RC3_API_R3.md) after `8ec9978` on
`codex/rc3-api-r1`. Consumer only; core promotion requires owner approval.

## Technique

The ordinary `read_packet(output, capacity)` function copies eight bytes and
returns their count or a negative error. `process_packet()` saves the status and
computes a sum only for a complete packet. Packet metadata surrounds the array.
These functions run in the normal application loop; there are no debugger hooks.

[Scenario](../../tests/api-experiments/profile/tests/board/test_outputs.py):

1. Wait for natural function entry and verify its caller frame.
2. Read pointer and capacity arguments; validate them against a known RAM object.
3. Record mutation intent; write strictly within the output array.
4. Execute `return <status>` and verify that the caller frame is selected.
5. Reach the next handler entry; check status, computed result, buffer bytes and
   unchanged adjacent metadata.
6. Allow another natural call and confirm normal behavior.

| Trial | Data and status | Caller verification |
| --- | --- | --- |
| NATURAL | Normal eight bytes,8; natural `finish` | Total770 |
| OUTPUT | Bytes1…8, forced status8 | Total36 |
| ERROR | Eight0xa5 bytes, status−5 | Status−5 saved; total remains at initial0 |
| SHORT | Bytes10,20,30 and0xa5 tail, status3 | Incomplete packet rejected; total remains0 |

After each trial the next natural call yields status8 and total770.
Adjacent `format` and `destination` fields remain intact in every case.

## Applicability limits

This can model a failure, short response or chosen device data without changing
caller code. There is no actual SPI/I2C/DMA here: the experiment establishes control
of ordinary C processing flow, not peripheral driver correctness.

`return` does not undo actions before the breakpoint. A real driver requires
inspection of the prologue, locks, resources and side effects. Our stopped call
has not filled the buffer yet; the observation applies to the particular `-Og` ELF.
Substitution must remain until the caller reads it; early rollback would invalidate
the trial. An argument pointer alone does not authorize arbitrary memory writes:
here exact address equality, capacity8 and known object bounds are checked.

SHORT models an incomplete response status and unusable tail by writing the whole
buffer. It does not prove a partial write by the driver itself. ERROR checks data
rejection after startup; retaining a previous nonzero result was not separately
tested. Only `int32_t` returns are covered; other ABIs, structs and floats come later.

## Results and observed limitation

R4: **32/32 HW PASS**,16 each on GDB14/Python3.11 and GDB16/Python3.13.
ELF SHA256: `893444194ffab90c1977d13d5aef1a47e50adcb33261c20f85090fe17095f2ae`.
Windows/Linux build/host/prepare: **24/24 PASS** (22 prepare, traceability,
20 host regressions grouped into one CTest); affected C format PASS. The earlier
overall format FAIL remains a separate limitation.

Regression on the new ELF, GDB16 only:

| Suite | Interface | Actual result |
| --- | --- | --- |
| R1 | native DAP | 24/24 PASS |
| R2 | native DAP | 7 first-round PASS; ASM ERROR stopped the series |
| R2 ASM separately | HLA | 4/4 PASS |
| R3 | native DAP | 16/16 PASS |

On native DAP, `jump` reached Default_Handler; self-branch recognition and the
first `stepi` passed. On the next `stepi`, OpenOCD reported `target not halted`,
then the external20s timeout fired. The original ERROR is retained; restoration
passed. With the same ELF, HLA completed all three steps in each of four runs.
This is an observed interface difference, not proof of an OpenOCD or ST-Link root
cause. Native DAP is not declared a universal replacement for HLA.
All five series completed restore HW_BOOT/HW_GPIO PASS; no software Z0 insertions
were found after RSP tracing began. Full R1–R3 was not rerun on GDB14.

## Checks and reproduction

Same F411CE/ST-Link/OpenOCD0.12.0, native DAP/SWD1MHz, Windows; GDB14 and GDB16,
one new GCC13 firmware, soft-float, `-Og -g3 -fno-lto`.
Add `--suite r4 --native-stlink` to the [R1 command](RC3_API_R1.md#reproduction).
Four scenarios × initial run plus three repeats × two GDB versions.

Actual versions, ELF SHA256, sources and results are in the
[sanitized summary](../research/rc3-r4-results.json). Raw logs remain locally in
`tests/api-experiments/build/evidence/`; the summary lists series directories.
Each series restores the agreed firmware and checks HW_BOOT/HW_GPIO and reset_run.
Earlier R1–R3 protocols retain their original ELF identities.

Public API, specification and package version are unchanged. Next are return types,
including 64-bit integers, floats and structs, assessed separately for natural
returns, forced returns and direct calls.
