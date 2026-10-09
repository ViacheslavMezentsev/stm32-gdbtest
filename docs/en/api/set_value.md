# set_value — removed name

[API](index.md) · [Русский](../../ru/api/set_value.md)

`set_value(expression, value) -> None`

Historical behavior before 0.4.0; use the migration example below in new scenarios.

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| API specification contract | 0.1.0; §4.6 |
| API_VERSION | 1 |
| Status | Available through 0.3.0; removed from the 0.4.0 candidate (`API_VERSION=2`) |
| Migration | `write(path, value)` returns a result and verifies the write when SRAM readback is available |

## Purpose

Reads expression before the write, executes GDB set variable using value, then reads it again. Records expression/value/before/after in mutations.

## Contract and limitations

value is interpolated into a GDB command: use a number or valid C expression. No automatic equality assertion or rollback. The author checks MMIO validity and HAL preconditions; reads can also affect registers.

## Migration example

```python
saved = t.read("board_adc_sequences")
try:
    t.write("board_adc_sequences", 0)
    t.check("counter injected", t.read("board_adc_sequences"), 0)
finally:
    t.write("board_adc_sequences", saved)
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.6.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/firmware/profiles/f411ce/tests/board/test_sleep.py).
- [value](value.md), [check](check.md), [force_return](force_return.md).
