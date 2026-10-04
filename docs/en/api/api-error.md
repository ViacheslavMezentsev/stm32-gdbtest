# api-error

[API](index.md) · [Русский](../../ru/api/api-error.md)

`ApiError(Exception): error.details; error.__cause__`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Describes an API operation failure separately: what was done, at which stage, with which effect and
why.

## Contract and limitations

The `operation`, `stage`, `effect`, `code` fields and details are available through `details`; the
original debugger error is kept as the cause.

Limitations: the full code and wording set is still being agreed; `effect` reports only the observed
effect (`none`, `unknown`, `partial`, `applied`); a failure does not roll back effects that already
happened.

## Example

```python
try:
    target.write("app_state.ticks", 1 << 40)
except ApiError as error:
    target.check("operation", error.details["operation"], "write")
```

An operation failure differs from a check mismatch: the former is `ApiError`, the latter is
`CheckFailed`.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
