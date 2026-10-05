# within, near, one_of

[API](index.md) · [Русский](../../ru/api/matchers.md)

`within(low, high)`, `near(value, tolerance)`, `one_of(*options)` — `from stm32_gdbtest import within, near, one_of`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core); imported without GDB |
| API specification contract | revision 0.3.4, item 4.1.2 |
| API_VERSION | 1 |
| Basis | the verification firmware `tests/firmware`, scenarios `HW_CI_PROFILE`, `HW_CI_ADC_SERIES`, `HW_CI_ADC_UNITS` |

## Purpose

Expectations for [check](check.md) beyond equality: a range, a tolerance and a set of options. The
report keeps the actual value and the bounds instead of `True`.

## Contract and limitations

- `within(low, high)` — numbers (not `bool`), `low <= high`; passes `low <= actual <= high`.
- `near(value, tolerance)` — a number and a non-negative tolerance; passes `abs(actual - value) <= tolerance`.
- `one_of(*options)` — at least one option; passes when `actual` equals one of them.

A non-numeric `actual` for `within`/`near` is a mismatch, not a Python exception. Invalid bounds, a
negative tolerance or an empty option set raise `ApiError` of operation `check` when the matcher is
created (`invalid_bounds`, `invalid_tolerance`, `invalid_options`). A matcher may be kept in a module
constant and used in several checks and table rows.

## Example

```python
from stm32_gdbtest import case, near, one_of, within

PLAUSIBLE_VDDA_MV = within(2800, 3600)

t.check("VDDA, mV", t.read("board_adc_reading.vdda_mv"), PLAUSIBLE_VDDA_MV)
t.check("core clock", t.read("SystemCoreClock"), near(16_000_000, 160_000))
t.check("quality", t.read("board_adc_reading.quality"), one_of(1, 2, 3))
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.4, item 4.1.2.
- [check](check.md).
