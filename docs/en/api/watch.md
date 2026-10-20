# watch

[API](index.md) · [Русский](../../ru/api/watch.md)

`watch(path) -> Point`

**Available since:** 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`; a point condition is evaluated without function calls.

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
with t.watch("app_state.ticks"):
    t.resume()
```

An interface refusal is reported as an operation failure naming the backend, not as a silent absence
of stops.

PC / frames: [TECH-013](../TESTING_TECHNIQUES.md#tech-013).

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md).
