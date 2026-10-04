# finish

[API](index.md) · [Русский](../../ru/api/finish.md)

`finish() -> dict`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Runs the rest of the current function and returns control to the caller with a result.

## Contract and limitations

The result describes the reached frame and the returned value when it is available.

Limitations: the value may be unavailable (optimization, missing debug information) — then it is
marked unavailable instead of being replaced by zero; a function that does not return ends with the
scenario timeout.

## Example

```python
target.reach("app_step")
target.finish()
target.check("returned to the caller", target.frames()["frames"][0]["function"],
             "app_receiver_step")
```

An unavailable return value is a separate result state.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
