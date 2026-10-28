# Buffer and repeated consumption

[Русский](README.md) · [TECH-004](../../docs/en/TESTING_TECHNIQUES.md#tech-004)

A5.3, 0.6.0 candidate. One neutral C++ module is built for host and for Cortex-M3 in
Renode. The library core is unchanged; no boards, UART, DMA, interrupts, RTOS or
instruments take part. Checkpoint functions belong to the teaching workload only.

## What the experiment proves

A prepared packet is placed in the experiment-owned buffer `inject_buf`, and the handler
`handle_packet` is called explicitly through `Pointer("inject_buf", count=N)` with the exact
length and signature. The ordinary application path (`receive` → `handle_packet(rx_buf, …)`)
is the neighbour: after the stimulus it must process the next packet as usual.

| Scenario | Independent expectation | Outcome |
| --- | --- | --- |
| HW_BUFFER_BASELINE | No stimulus, one ordinary packet: accepted=1, sequence=1, type 0x10 | PASS |
| HW_BUFFER_PACKETS | Two experiment packets in order (0x21, then 0x22), then the ordinary one: sequence=3 | PASS |
| HW_BUFFER_REJECT | A bad checksum is rejected without changing the result; the next packet is accepted | PASS |
| HW_BUFFER_REENTRY | A nested call during ordinary processing is rejected; the current packet completes | PASS |
| HW_BUFFER_BOUNDS | A 17-element Pointer into a 16-element array is refused before the call: entries=0 | PASS |
| HW_BUFFER_UNCONSUMED | The packet is written without a call; expecting its consumption is wrong | intentional FAIL |
| HW_BUFFER_EXCEPTION | Buffer write, then a deliberate Python exception before the call | intentional ERROR |

A successful call is followed by checks of the return value, counters, guard words
around the buffer, the experiment buffer staying untouched by the ordinary path, and
the next ordinary packet. The nested call runs at a stop inside ordinary processing
(`inside_handler`): it checks the re-entry guard, it does not reproduce an interrupt.

All mutable data lie contiguously in the `.experiment` section (76 bytes): guard words,
the experiment buffer, the ordinary buffer, the length and the handler state. The scenario
first checks for gaps using ELF addresses and sizes, then snapshots the whole section and
restores it in finally, also after FAIL/ERROR; the journal keeps SHA-256 before and after.
This restores data; it does not rewind PC or the stack.

## Running

```powershell
python tests/buffer-consumption/run.py --host-only
python tests/buffer-consumption/run.py --toolchain <GCC-directory> --renode <path-to-Renode>
```

Linux takes the same arguments. The host runs the same packet processing and a model of
the re-entry flag, but it does not test GDB call or Pointer. Real memory/call go through
the ordinary runner in Renode; every scenario gets a fresh ELF session and the seven are
repeated twice: 10 PASS, 2 expected FAIL, 2 expected ERROR. Artifacts: build/buffer-consumption/<UTC>/.

The analysis uses the shared result/records readers and checks integrity, completeness,
the early Pointer refusal, packet order, return values, counters and restoration. Source
FAIL/ERROR outcomes are not rewritten; a campaign PASS means the expected matrix matched.

## DDTT boundaries

The evidence is software-buffer: the handler's reaction to prepared data. DMA did not
take part, so DMA operation, buffer ownership transfer and stream stop are not tested.
Interrupt context, peripheral reception and physical signals are excluded as well. An
active DMA needs its own order: stop the stream, take the buffer, prepare data, return
ownership and restore state. The observation record keeps method, packets, return values,
counters and excluded layers; this is an example convention, not a new runner schema.
