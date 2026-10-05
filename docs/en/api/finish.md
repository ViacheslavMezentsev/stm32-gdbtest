# finish

[API](index.md) · [Русский](../../ru/api/finish.md)

`finish() -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.2.9 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Runs the rest of the current function and returns control to the caller with a result.

## Contract and limitations

The result describes the reached frame (`function`), the function that returned (`returned_from`) and the
returned value. The value comes from the GDB value history ("Value returned is $N"), present in every supported
version; `return_state` is `available`, `void` (by the declared type) or `unavailable`. On GDB 14 the stop event
carries no reason: the return is proven by the changed frame, the stop is marked `inferred` and the report gets
one `inferred_stop` warning. The reference version is GDB 15.2 (xPack 14.2.1).

Limitations: the value may be unavailable (optimization, missing debug information) — then it is
marked unavailable instead of being replaced by zero; a function that does not return ends with the
scenario timeout.

## Example

```python
t.reach("app_step")
t.finish()
t.check("returned to the caller", t.frames()["frames"][0]["function"],
             "app_receiver_step")
```

An unavailable return value is a separate result state.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
