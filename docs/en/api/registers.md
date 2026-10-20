# registers

[API](index.md) · [Русский](../../ru/api/registers.md)

`registers(*names, frame=None) -> dict`

**Available since:** 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`.

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
pc, sp = t.registers("pc", "sp").values()
r0 = t.registers("r0")["r0"]
```

Registers that do not exist on the given core produce diagnostics, not an empty value.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md).
