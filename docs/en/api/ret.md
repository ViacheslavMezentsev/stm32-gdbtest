# ret

[API](index.md) · [Русский](../../ru/api/ret.md)

`ret(value=None) -> dict`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Returns control early from the current function, substituting a value when given, and describes the
result.

## Contract and limitations

The value is encoded by the function's return type and checked before it is applied; the result
reports that the value was applied, and the receiver is the calling code.

Limitations: the value must fit the return type, otherwise it fails with `out_of_range`; the rest of
the function is skipped and completed effects are not rolled back; the caller's use of the value
depends on the caller's code — verifying it needs a calling function that stores the value.

## Example

```python
target.reach("app_step")
target.ret(42)
target.reach("app_step")
target.check("the caller stored it", target.value("app_received.produced"), 42)
```

A forced return is not `finish` and does not run the rest of the function.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
