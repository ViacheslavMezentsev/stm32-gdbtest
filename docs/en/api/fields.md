# fields — removed name

[API](index.md) · [Русский](../../ru/api/fields.md)

`fields(expression, expected) -> None`

Historical behavior before 0.4.0; use the migration example below in new scenarios.

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| API specification contract | 0.1.0; §4.3 |
| API_VERSION | 1 |
| Status | Available through 0.3.0; removed from the 0.4.0 candidate (`API_VERSION=2`) |
| Migration | `check(rows)` for comparisons; `read(path, fields=…)` only reads |

## Purpose

expected maps field paths to integers or C-expression strings. Reads and compares fields sequentially in mapping order.

## Contract and limitations

The former method evaluated string expectations as expressions rather than comparing text. The first error/FAIL stopped iteration. Multiple reads were not an atomic snapshot.

## Migration example

```python
t.reach("HAL_GPIO_Init")
t.check([
    ("GPIO pin", "GPIO_Init->Pin", 1 << 5),
    ("GPIO mode", "GPIO_Init->Mode", "GPIO_MODE_OUTPUT_PP")
])
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.3.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/hal-f030/profile/tests/board/test_hal_methods.py).
- [check](check.md), [value](value.md).
