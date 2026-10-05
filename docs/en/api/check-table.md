# check_table

[API](index.md) · [Русский](../../ru/api/check-table.md)

`check_table(rows) -> int`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | revision 0.3.3 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the verification firmware `tests/firmware`, scenarios HW_CI_INIT, HW_CI_LED_GPIO (all profiles) |

## Purpose

A table of "name, actual, expected" rows without local helpers in scenarios.

## Contract and limitations

`rows` is a non-empty list/tuple of three-element rows. String `actual` and `expected` cells are
evaluated as GDB expressions through `evaluate` (declared type); other cells are used as they are.
Rows are checked in order through `check`; the first mismatch stops the scenario (`CheckFailed`).
The row structure is validated before the first evaluation (`ApiError`, `invalid_rows`). Returns the
number of checked rows.

## Example

```python
target.check_table([
    ("initialized interval", "app_delay", "EXPECTED_DELAY"),
    ("BSS loop count", "app_state.ticks", 0),
    ("PA5 output", "(GPIOA->MODER & GPIO_MODER_MODER5) == GPIO_MODER_MODER5_0", 1),
])
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.3, items 4.1.3.
