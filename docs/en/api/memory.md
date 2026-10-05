# memory

[API](index.md) · [Русский](../../ru/api/memory.md)

`memory(address, size) -> bytes; write_memory(address, data, *, verify=True) -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | revision 0.3.3 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the verification firmware `tests/firmware`, scenarios HW_CI_PROFILE |

## Purpose

Raw bytes of buffers and of the image: snapshots, CRCs, signatures.

## Contract and limitations

`memory` reads 1 to 4096 bytes inside the SRAM window (`0x20000000..0x20100000`) or the profile
flash (`flash_start`, `flash_size`). `write_memory` writes into SRAM only, reads back and logs the
change in `report["mutations"]` (bytes as hex). Peripheral addresses are refused (`outside_window`):
reading a register may change the device state. An invalid block raises `invalid_block`, a GDB refusal
`read_failed`/`write_failed`, a read-back mismatch `verification_failed`.

## Example

```python
vectors = target.memory(target.profile["flash_start"], 8)
target.check("initial SP in SRAM", 0x20000000 <= int.from_bytes(vectors[:4], "little") < 0x20100000, True)
address = target.symbol("app_state")["address"]
target.write_memory(address, bytes(4))
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.3, items 4.16.1–4.16.3, 6.8.
