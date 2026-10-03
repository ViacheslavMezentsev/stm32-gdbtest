# reach

[API](index.md) · [Русский](../../ru/api/reach.md)

`reach(function, when=None) -> None`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| Contract in API specification | 0.1.0; §4.5 |
| API_VERSION | 1 |

## Contract

Sets a temporary hardware breakpoint, continues once, then checks its number, frame name and optional when condition.

An unrelated stop is not automatically skipped. Frame comparison strips clone suffixes, parameters and const/volatile. The point is removed on exit. No per-call timeout argument: the scenario deadline applies.

## Example

```python
target.reach("board_adc_sample")
target.reach("board_delay_ms")
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.5.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py).
- [breakpoint](breakpoint.md), [case](case.md).
