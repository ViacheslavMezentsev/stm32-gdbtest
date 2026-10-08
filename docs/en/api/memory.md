# memory

[API](index.md) · [Русский](../../ru/api/memory.md)

`memory(address, size | data, *, verify=None) -> bytes | dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | revision 0.3.4, items 4.16.1–4.16.4, 6.8 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the verification firmware `tests/firmware`, scenarios `HW_CI_PROFILE`, `HW_CI_CALL_PREDICATE` |

## Purpose

Raw bytes of buffers and of the image: snapshots, CRCs, signatures, restoring a saved state.

## Contract and limitations

The type of the second argument decides the operation:

| Second argument | Operation | Result |
| :--- | :--- | :--- |
| `int` (not `bool`), 1..4096 | read that many bytes from the SRAM window or the profile flash | `bytes` |
| `bytes`, `bytearray`, `memoryview` | write the bytes into SRAM; read back unless `verify=False`; log in `report["mutations"]` | `{"operation": "memory", "address", "size", "verified"}` |
| anything else (`str`, `list`, `bool`, `float`) | refused before the memory is touched (`invalid_block`) | — |

A list of numbers is not accepted: the element width would be a guess. Build bytes explicitly:
`value.to_bytes(4, "little")`, `struct.pack("<HI", a, b)`, `bytes(8)`. `verify` applies to a write
only; passing it with a size is refused (`invalid_verify`).

The SRAM window is `0x20000000..0x200FFFFF`; the flash window comes from `flash_start` and
`flash_size` of the profile and is read-only. Peripheral addresses are refused (`outside_window`):
reading a register may change the device state. A GDB refusal raises `read_failed`/`write_failed`,
a read-back mismatch `verification_failed` with `effect="applied"`.

## Example

```python
state = t.symbol("app_state")
snapshot = t.memory(state["address"], state["size"])      # read: bytes
t.call("app_step", "&app_state", "APP_MODE_BLINK")
t.memory(state["address"], snapshot)                     # write: restore the saved bytes
vectors = t.memory(t.profile["flash_start"], 8)
initial_sp = int.from_bytes(vectors[:4], "little")  # A stack-top pointer, not a readable byte address.
```

Initial SP and readable-block bounds require different checks: [TECH-017](../TESTING_TECHNIQUES.md#tech-017).

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.4, items 4.16.1–4.16.4, 6.8.
- [symbol](symbol.md), [write](write.md).
