# force_return

[API](index.md) · [Русский](../../ru/api/force_return.md)

`force_return(expression) -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| Contract in API specification | 0.1.0; §4.7 |
| API_VERSION | 1 |
| Former-name alias | `ret(value=None)`; the alias works without warnings until 1.0, removal in 0.4.0; added by revision 0.3.0 |

## Contract

Executes GDB return with expression and records the operation, function name and expression in mutations. Use an empty string for void.

Return affects the selected frame; the log takes the newest_frame name. Keep the frame selection unchanged for consistent naming. Skips remaining code without undoing prior effects. GDB must support the type/ABI; this is not finish.

## Example

```python
target.reach("HAL_ADC_Start_DMA")
target.force_return("(HAL_StatusTypeDef)1")
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.7.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/hal-f030/profile/tests/board/test_hal_methods.py).
- [reach](reach.md), [set_value](set_value.md).
