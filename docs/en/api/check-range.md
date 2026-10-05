# check_range

[API](index.md) · [Русский](../../ru/api/check-range.md)

`check_range(name, actual, low, high); check_near(name, actual, expected, tolerance); check_in(name, actual, options)`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | revision 0.3.3 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the verification firmware `tests/firmware`, scenarios HW_CI_PROFILE, HW_CI_ADC_SERIES |

## Purpose

Checks with bounds: the report keeps the actual value and the bounds instead of `True`.

## Contract and limitations

- `check_range`: passes when `low <= actual <= high`; the report `expected` is `{"low", "high"}`.
- `check_near`: passes when `|actual - expected| <= tolerance`; `expected` is `{"value", "tolerance"}`.
- `check_in`: passes when `actual` equals one of `options` (a non-empty list/tuple/set); `expected` is `{"in": [...]}`.

The `report["checks"]` entry gains a `kind` field (`range`, `near`, `in`). A non-numeric `actual` in
`check_range`/`check_near` is a mismatch (`CheckFailed`), not a Python exception. Invalid bounds, a
negative tolerance or an empty option set raise `ApiError` of operation `check` (`invalid_bounds`,
`invalid_tolerance`, `invalid_options`) without a report entry.

## Example

```python
vdda = target.read("sensor.vdda_mv")
target.check_range("VDDA, mV", vdda, 2900, 3600)
target.check_near("temperature, C", target.evaluate("sensor.temp", as_type=float), 25.0, 15.0)
target.check_in("mode", target.read("app_mode"), ("APP_MODE_IDLE", "APP_MODE_BLINK"))
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.3, items 4.1.2.
