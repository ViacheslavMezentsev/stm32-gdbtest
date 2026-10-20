# CheckFailed

[API](index.md) · [Русский](../../ru/api/check-failed.md)

`CheckFailed(ApiError, AssertionError): error.name; error.details`

**Available since:** 0.1.0-rc.1; public import since 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`.

## Purpose

Reports that a scenario check did not match the expectation and is recorded in the report as a failed
check.

## Contract and limitations

The exception carries the check name (`name`) and its data in `details` (`check`, `actual`, `expected`,
`code=mismatch`). Compatibility is preserved: `CheckFailed` remains a subclass of `AssertionError` and
`ApiError`, so scenarios that catch `AssertionError` keep working.

Limitations: a failed check does not stop the run immediately when the scenario continues, but the run
outcome is a failure; `actual` and `expected` go into `details` unchanged and must be serializable by
the report.

## Example

```python
t.check("ticks advanced", t.read("app_state.ticks") > 0, True)
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md).
