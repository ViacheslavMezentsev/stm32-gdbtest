# reach

[API](index.md) · [Русский](../../ru/api/reach.md)

`reach(location, condition=None) -> dict`

**Available since:** 0.1.0-rc.1; waiting and `condition` since 0.3.0 · **API 3 (0.5.0):** in `async def` use `await t.reach(…)`, in `def` the synchronous form is unchanged; a condition is evaluated without function calls. [Sync/async rules](../LIVE_EXECUTION.md).

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

## C++ names in GDB quotes (0.4.0)

One outer pair of GDB single quotes is ignored when comparing the frame name:
`t.reach("'Converter::apply(float) const'")`. The original string is passed unchanged to GDB
and returned in `location`; `stop.frame` retains GDB's name. This is not a general linespec
parser: point-number and normalized-frame checks remain mandatory.
With 0.3.0 use the unquoted form.
[Example](../../../tests/cpp-context/profile/tests/board/test_cpp_context.py).

Compact result storage and console control do not remove checks; see [result journal](../API.md#result-journal-and-output-060-candidate-a22).
