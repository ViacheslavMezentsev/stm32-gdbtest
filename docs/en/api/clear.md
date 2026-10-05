# clear

[API](index.md) · [Русский](../../ru/api/clear.md)

`clear() -> None`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| API specification contract | 0.1.0; §4.8 |
| API_VERSION | 1 |
| Basis | the effective 0.1.0/0.2.0 contract and the scenarios of the verification firmware `tests/firmware` |

## Purpose

Deletes all still-valid Target-owned breakpoints and clears ownership.

## Contract and limitations

Also removes fault guards installed by the agent. Leaves unrelated GDB points alone. Does not reset the MCU or clear records. Use for an intentional change of stop strategy.

## Example

```python
# Deliberately remove all Target stops, including fault guards.
target.clear()
target.reach("board_adc_sample")
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

This is an illustrative fragment; no separate hardware run of it is claimed.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.8.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../stm32_gdbtest/target.py).
- [breakpoint](breakpoint.md), [reach](reach.md), [records](records.md).
