# value

[API](index.md) · [Русский](../../ru/api/value.md)

`value(expression) -> int`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| Contract in API specification | 0.1.0; §4.2 |
| API_VERSION | 1 |
| Former-name alias | value(expression) -> read(path) (the alias works without warnings until 1.0; removal in 0.4.0) |

## Contract

expression is a GDB/C expression string in the current context. Evaluates it, fetches a lazy value and converts it to int.

Stop the MCU for consistent reads. Optimized-out or missing symbols fail rather than return zero. This is not typed float/structure reading; expressions may have side effects.

## Example

```python
sequence = target.value("board_adc_sequences")
target.check("nonnegative sequence", sequence >= 0, True)
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.2.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py).
- [check](check.md), [fields](fields.md), [record](record.md).
