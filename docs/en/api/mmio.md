# mmio.read / mmio.write

[API](index.md) · [Русский](../../ru/api/mmio.md)

`t.mmio.read(name, *, allow_effects=False, override=None, reason=None) -> int`; `t.mmio.write(name, value, *, allow_effects=False, override=None, reason=None) -> dict`

**Available since:** 0.5.0 · **API 3 (0.5.0):** new in 0.5.0; no `await`; needs an SVD in `session.toml` (`[mmio] svd`).

```python
value = t.mmio.read("GPIOA.IDR")
ack = t.mmio.write("GPIOA.BSRR", 1)
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
t.mmio.write("MODEL.WO", 7, override=reg,
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

## Reason and combined failures (0.6.0 candidate)

`reason` is allowed without `override`: a nonblank string is captured in
`mmio.attempt` without changing SVD permissions or effect consent. Invalid values
without override yield `invalid_reason` before transport; override still requires a reason.
If transport and result auditing both fail, the caller receives `transport_failed`
(transport/unknown), the transport cause in `__cause__`, and the audit failure in
`details.audit_error`. No retry occurs. Otherwise the existing `journal_unavailable`
with effect=none/unknown before/after transport is preserved. ACK does not prove a
physical effect.

## A2.1 candidate

API schema 2 adds compact MMIO and larger budgets; schema 1 keeps its limits. Logical rows stay unchanged; compact materialization has a separate bound. [Configuration, migration and common reader](../API.md#a21-compact-journal-060-candidate).

## Modeled GPIO input and override (A5.2)

The [executable example](../../../tests/modeled-gpio/README.en.md) separates external
model input from SRAM/return substitution. Check source → register → firmware
consumption, the next input and an unaffected neighbour. `override` replaces the
SVD description, not device behavior: an ignored IDR write may receive an ACK.
Preserve the false claim as FAIL; separate analysis checks the expected lack of effect.
Restore both firmware state and external input. The model proves no electrical/timing properties.
