# mmio.read / mmio.write

[API](index.md) · [Русский](../../ru/api/mmio.md)

Available in the 0.5.0 candidate; API specification 0.3.21 §4.21; API_VERSION=3.

```python
value = target.mmio.read("GPIOA.IDR")
ack = target.mmio.write("GPIOA.BSRR", 1)
```

Names are exact register names from the [SVD snapshot](../SVD.md), not GDB expressions.
Signatures: `read(name, *, allow_effects=False, override=None, reason=None) -> int`,
`write(name, value, *, allow_effects=False, override=None, reason=None) -> dict`.
Reads return unsigned integers. Writes accept Python int only (not bool), fitting the
width; return address, width in bits, value, acknowledged=True, verified=False.
ACK confirms the server reply, not the device state.

## Before access

SVD supplies address, 8/16/32-bit width, permissions and effects. Validation checks
alignment, 32-bit address range, value range, register and all field permissions.
Missing rights, overlapping fields and unsupported descriptions are rejected.
A WO field blocks whole-register reads; a RO field blocks writes.
writeOnce/read-writeOnce writes are rejected because history is unknown.
writeConstraint blocks writes until constraint enforcement is implemented.
Any readAction or modifiedWriteValues, including field-level effects, requires
allow_effects=True. Consent does not bypass other checks.

Requires little-endian Cortex-M, the main GDB Python thread, stopped threads in the
selected inferior and RemoteTargetConnection.send_packet. These checks run before
each operation; there is no user-supplied route-ready flag.
Peripherals and DMA may continue while the core is halted.

## Transport and errors

An accepted operation calls send_packet once: RSP m for reads or M for writes,
bypassing GDB memory caches and expression evaluation. No before read, readback,
RMW, retry or automatic restoration. Read replies must contain exactly the requested
bytes; write replies must be OK.

The guarantee ends at the request to GDB: physical bus width/count, adapter
transformations and retries inside GDB transport are not guaranteed. SVD can be
incorrect. Qualify the route in Renode and separately on the target board using the
[MMIO method](../MMIO.md); model PASS is not HW PASS.

MMIOError derives from ApiError and is exported by stm32_gdbtest. details contains
operation=mmio.read/mmio.write, code, stage, effect; __cause__ retains the cause.
Before access: effect=none, stage=validation (including unqualified_context).
Failure/short reply after sending: transport_failed, stage=transport, effect=unknown.
Do not retry automatically: a FIFO read may already have consumed an item.

Before sending, mmio.attempt records original/effective descriptions, SVD SHA-256,
override reason and write value; mmio.result follows. Validation refusals are not
transport attempts and do not produce these entries.
Journal failure before sending: journal_unavailable/audit/none; afterwards: audit/unknown.
Two entries consume the shared records budget. Enable [results] capture=true so the
runner saves records.json, including ERROR. Without capture the journal is in memory
only. Budget exhaustion is never hidden.

## Correcting an incorrect SVD

```python
from stm32_gdbtest import MMIORegister
reg = MMIORegister("MODEL.WO", 0x40000004, 32, "write-only")
target.mmio.write("MODEL.WO", 7, override=reg,
                  reason="Teaching model supports writes; source SVD is incorrect")
```

MMIORegister is immutable: name, address, width, access, read_action=None,
write_effect=None, fields=(), constraint=False. Each field is a tuple of
(name, bit_offset, bit_width, access, read_action, write_effect, constraint).
Override requires a nonblank reason and a matching name; it works without SVD.
It replaces the entire description, but preserves address/width/permission/effect,
halt/transport/journal validation. No safety=False or string assignments.

## Reproduction

[Teaching model and commands](../../../tests/mmio-renode/README.md): WO, RTC, FIFO,
W1C, 8/16/32 bits, inheritance, lost ACK and incorrect SVD. Host regression:
`python -m unittest discover -s tests/host -p test_mmio.py`.

The connection must serve exactly one inferior: raw packets do not select a process on a multiprocess remote server.

Hardware acceptance on 2026-10-16: six MCUs, 141 assertions for the selected 32-bit GPIO/DMA route, recovery VERIFIED. Scope and matrix: [API_ACCEPTANCE](../API_ACCEPTANCE.md).
