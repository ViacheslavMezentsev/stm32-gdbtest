# force_return — removed name

[API](index.md) · [Русский](../../ru/api/force_return.md)

`force_return(expression) -> dict`

Historical behavior before 0.4.0; use the migration example below in new scenarios.

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| API specification contract | 0.1.0; §4.7 |
| API_VERSION | 1 |
| Status | Available through 0.3.0; removed from the 0.4.0 candidate (`API_VERSION=2`) |
| Migration | `ret(value=None)` returns an operation result; check the type and selected frame |

## Purpose

Executes GDB return with expression and records the operation, function name and expression in mutations. Use an empty string for void.

## Contract and limitations

Return affects the selected frame; the log takes the newest_frame name. Keep the frame selection unchanged for consistent naming. Skips remaining code without undoing prior effects. GDB must support the type/ABI; this is not finish.

## Migration example

```python
t.reach("HAL_ADC_Start_DMA")
t.ret("(HAL_StatusTypeDef)1")
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.7.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/hal-f030/profile/tests/board/test_hal_methods.py).
- [reach](reach.md), [set_value](set_value.md).
