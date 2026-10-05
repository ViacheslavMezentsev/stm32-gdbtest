# value

[API](index.md) · [Русский](../../ru/api/value.md)

`value(expression) -> int`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| API specification contract | 0.1.0; §4.2 |
| API_VERSION | 1 |
| Basis | the effective 0.1.0/0.2.0 contract and the scenarios of the verification firmware `tests/firmware` |
| Former-name alias | value(expression) -> read(path) (the alias works without warnings until 1.0; removal in 0.4.0) |

## Purpose

expression is a GDB/C expression string in the current context. Evaluates it, fetches a lazy value and converts it to int.

## Contract and limitations

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
- [Scenario or implementation check](../../../tests/firmware/common/tests/board/test_measurements.py).
- [check](check.md), [fields](fields.md), [record](record.md).
