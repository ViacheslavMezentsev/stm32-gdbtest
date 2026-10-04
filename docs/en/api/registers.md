# registers

[API](index.md) · [Русский](../../ru/api/registers.md)

`registers(*names, frame=None) -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.3.0 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Reads the registers of the selected frame as one dict: the program counter, the stack pointer and
the general-purpose registers.

## Contract and limitations

The program counter is read through the frame accessor; the stack pointer and general-purpose
registers are read by name. The observed scalar type codes of the core are accepted.

Limitations: right after a reset or a forced return the program counter from the frame and from a
direct register read can disagree — the frame is the source of truth; register names depend on the
core architecture.

## Example

```python
pc, sp = target.registers("pc", "sp").values()
r0 = target.registers("r0")["r0"]
```

Registers that do not exist on the given core produce diagnostics, not an empty value.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
