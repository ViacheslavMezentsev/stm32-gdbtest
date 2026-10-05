# watch

[API](index.md) · [Русский](../../ru/api/watch.md)

`watch(path) -> Point`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.3.0 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Sets a watchpoint on an object in order to stop when it changes.

## Contract and limitations

It returns a point object; the stop is classified as a watch event and is available to the scenario.

Limitations: only addressable objects up to eight bytes with natural alignment can be watched; J-Link
reports the watch point as an ordinary point with its number; OpenOCD (HLA) delivers an event without a point
number, in which case the stop is confirmed by the changed watched object and marked `inferred`, while
`native_reason` keeps only what GDB reported; a reset is refused while a watchpoint is active. Write watch points are verified
on the OpenOCD and J-Link stands of the project.

## Example

```python
with target.watch("app_state.ticks"):
    target.resume()
```

An interface refusal is reported as an operation failure naming the backend, not as a silent absence
of stops.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.0.
