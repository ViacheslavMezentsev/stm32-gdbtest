# check

[API](index.md) · [Русский](../../ru/api/check.md)

`check(name, actual, expected) -> None`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| Contract in API specification | 0.1.0; §4.1 |
| API_VERSION | 1 |

## Contract

Compares actual and expected with ==, records and prints the result. name identifies the check.

A mismatch raises CheckFailed and ends the scenario with FAIL. Use JSON-report-compatible values. Does not return bool.

## Example

```python
target.check("initial count", target.value("board_adc_sequences"), 0)
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.1.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py).
- [value](value.md), [fields](fields.md).
