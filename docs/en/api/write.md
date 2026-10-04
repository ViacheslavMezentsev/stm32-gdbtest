# write

[API](index.md) · [Русский](../../ru/api/write.md)

`write(path, value, *, verify=True) -> dict`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Writes a value into an addressable program object and returns the result with effect diagnostics.

## Contract and limitations

With verification (`verify=True`) a read-back confirms the applied value.

Limitations: addressable objects in RAM of a declared scalar type; integer widths are in the
verified scope, 64-bit and `float` are not. A write failure is never hidden and is reported as an
operation failure; an already applied effect is not rolled back.

## Example

```python
target.write("app_state.ticks", 41)
target.write("app_delay", 100)
```

A write into an immutable area (Flash, read-only registers) ends with diagnostics, not with a silent
success.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
