# read

[API](index.md) · [Русский](../../ru/api/read.md)

`read(path, *, fields=None, start=0, count=None) -> scalar | list | dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.2.8 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Reads a value of the debugged program by name or expression and converts it to a plain Python type.

## Contract and limitations

It returns a scalar for integers, enumerations, booleans, floating-point numbers and pointers; a
list or a dict for arrays, structs and strings.

Limitations: addressable objects in RAM; the symbols and types must exist in the ELF; the profile's
registers and peripherals apply; slices, `const`/`volatile` and C++ are outside the verified scope.

## Example

```python
value = target.read("app_state.ticks")
temperature = target.read("board_adc_reading.temperature_mdeg_c")
```

A memory or conversion failure is reported as an operation failure; partially read data is never
reported as success.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
