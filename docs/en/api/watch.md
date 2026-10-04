# watch

[API](index.md) · [Русский](../../ru/api/watch.md)

`watch(path) -> Point`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Sets a watchpoint on an object in order to stop when it changes.

## Contract and limitations

It returns a point object; the stop is classified as a watch event and is available to the scenario.

Limitations: watchpoint support depends on the backend and the interface: an HLA server does not
watch memory, and the verified configuration is native DAP; only an addressable object is watched; a
reset is refused while a watchpoint is active.

## Example

```python
with target.watch("app_state.ticks"):
    target.resume()
```

An interface refusal is reported as an operation failure naming the backend, not as a silent absence
of stops.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
