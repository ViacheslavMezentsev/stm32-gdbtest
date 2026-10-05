# check

[API](index.md) · [Русский](../../ru/api/check.md)

`check(name, actual, expected) -> None`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| API specification contract | 0.1.0; §4.1 |
| API_VERSION | 1 |
| Basis | the effective 0.1.0/0.2.0 contract and the scenarios of the verification firmware `tests/firmware` |

## Purpose

Compares actual and expected with ==, records and prints the result. name identifies the check.

## Contract and limitations

A mismatch raises CheckFailed and ends the scenario with FAIL. Use JSON-report-compatible values. Does not return bool.

## Example

```python
target.check("initial count", target.value("board_adc_sequences"), 0)
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.1.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/firmware/common/tests/board/test_measurements.py).
- [value](value.md), [fields](fields.md).
