# check-failed

[API](index.md) · [Русский](../../ru/api/check-failed.md)

`CheckFailed(AssertionError)`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Reports that a scenario check did not match the expectation and is recorded in the report as a
failed check.

## Contract and limitations

The exception carries the check name and is available to the report together with the actual and
expected values.

Limitations: the strict check mode is still being agreed; a mismatch does not stop the run
immediately when the scenario continues, but the run outcome is a failure.

## Example

```python
target.check("ticks advanced", target.value("app_state.ticks") > 0, True)
```

A failed check differs from an operation failure: the scenario continues, but the run cannot be
successful.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
