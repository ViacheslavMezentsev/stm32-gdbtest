# test

[API](index.md) · [Русский](../../ru/api/test.md)

`test(identifier, *, timeout_s=20, labels=(), contracts=())`

| Property | Value |
| --- | --- |
| Module support | 0.3.0 (core) |
| API specification contract | not accepted; designed revision 0.3.0 |
| API_VERSION | 1 (the effective contract does not change) |
| Former-name alias | `case`; the alias works without warnings until 1.0, removal in 0.4.0 |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

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
def app_step_scenario(target):
    target.reach("app_step")
```

A scenario without a declaration is not part of the collection.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
