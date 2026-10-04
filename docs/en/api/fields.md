# fields

[API](index.md) · [Русский](../../ru/api/fields.md)

`fields(expression, expected) -> None`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| Contract in API specification | 0.1.0; §4.3 |
| API_VERSION | 1 |
| Former-name alias | fields(expression, expected) -> read(path, fields=…) (the alias works without warnings until 1.0; removal in 0.4.0) |

## Contract

expected maps field paths to integers or C-expression strings. Reads and compares fields sequentially in mapping order.

String expectations are evaluated through value, not compared as text. The first error/FAIL stops iteration. Multiple reads are not an atomic snapshot.

## Example

```python
target.reach("HAL_GPIO_Init")
target.fields("*GPIO_Init", {"Pin": 1 << 5, "Mode": "GPIO_MODE_OUTPUT_PP"})
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.3.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/hal-f030/profile/tests/board/test_hal_methods.py).
- [check](check.md), [value](value.md).
