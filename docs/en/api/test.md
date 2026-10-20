# test

[API](index.md) · [Русский](../../ru/api/test.md)

`test(identifier, *, timeout_s=20, labels=(), contracts=())`

**Available since:** 0.3.0 · **API 3 (0.5.0):** the function form selects the mode: `def` is synchronous, `async def` awaits navigation, `call`, `wait` and `halt`. [Sync/async rules](../LIVE_EXECUTION.md).

## Purpose

Declares a scenario: identifier, timeout, selection labels and the contracts it verifies.

## Contract and limitations

The identifier is unique within the collection; the timeout bounds the scenario run; labels and
contracts are used by selection and the report.

Limitations: the numeric timeout default is still being agreed; exceeding the timeout ends the
scenario with a failure instead of continuing; a duplicate identifier is detected when the
collection is assembled.

## Example

```python
@test("HW_APP_STEP", timeout_s=60, labels=("app",), contracts=("ci_app_api",))
def app_step_scenario(t):
    t.reach("app_step")
```

A scenario without a declaration is not part of the collection.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md).
