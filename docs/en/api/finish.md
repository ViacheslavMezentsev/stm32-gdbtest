# finish

[API](index.md) · [Русский](../../ru/api/finish.md)

`finish() -> dict`

**Available since:** 0.3.0 · **API 3 (0.5.0):** in `async def` use `await t.finish(…)`, in `def` the synchronous form is unchanged; a condition is evaluated without function calls. [Sync/async rules](../LIVE_EXECUTION.md).

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

- [API specification](../../TECHNICAL_SPECIFICATION_API.md).
