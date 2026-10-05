# reach

[API](index.md) · [Русский](../../ru/api/reach.md)

`reach(location, condition=None) -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| API specification contract | 0.1.0; §4.5; the result was added by designed revision 0.2.9 |
| API_VERSION | 1 |
| Basis | the effective 0.1.0/0.2.0 contract and the scenarios of the verification firmware `tests/firmware` |

## Purpose

Sets a temporary hardware breakpoint, continues once, then checks its number, frame name and optional condition (formerly when).

## Contract and limitations

An unrelated stop is not automatically skipped. Frame comparison strips clone suffixes, parameters and const/volatile. Only the point created by the call is removed on exit: a scenario point at the same place stays. No per-call timeout argument: the scenario deadline applies.

## Example

```python
t.reach("board_adc_sample")
t.reach("board_delay_ms")
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.5.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/firmware/common/tests/board/test_measurements.py).
- [breakpoint](breakpoint.md), [case](case.md).
