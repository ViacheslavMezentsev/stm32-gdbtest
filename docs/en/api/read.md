# read

[API](index.md) · [Русский](../../ru/api/read.md)

> **MMIO:** Composite reads may touch neighboring registers; volatile does not guarantee one access. [Limitations and model/board validation](../MMIO.md).

`read(path, *, fields=None, start=0, count=None) -> scalar | list | dict`

**Available since:** 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`; the expression cannot call target functions (`expression_call_forbidden`).

## Purpose

Reads a value of the debugged program by name or expression and converts it to a plain Python type.

## Contract and limitations

It returns a scalar for integers, enumerations, booleans, floating-point numbers and pointers; a
list or a dict for arrays, structs and strings.

Limitations: addressable objects in RAM; the symbols and types must exist in the ELF; the profile's
registers and peripherals apply; slices, `const`/`volatile` and C++ are outside the verified scope.

`fields` is a list of names (`fields=("ticks", "led")`) or a `{name: hint}` mapping; the result is a
dictionary of values by name.

Several independent objects at one stop are read with Python itself:
`dict(zip(paths, map(t.read, paths)))`; there is no separate list form of `read`.

## Example

```python
value = t.read("app_state.ticks")
temperature = t.read("board_adc_reading.temperature_mdeg_c")
```

A memory or conversion failure is reported as an operation failure; partially read data is never
reported as success.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md).
