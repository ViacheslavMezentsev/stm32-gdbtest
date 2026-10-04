# reset

[API](index.md) · [Русский](../../ru/api/reset.md)

`reset() -> dict`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Resets the target through the backend command, leaves the core halted and invalidates debugger
caches.

## Contract and limitations

Before the reset the scenario's active points are removed; after the command the register and frame
caches are invalidated, including after a failed attempt; the result describes the state and the
invalidation steps.

Limitations: the reset command comes from the stand configuration (`monitor reset halt` for OpenOCD,
`monitor reset` for J-Link); a stop before the program's first instruction is not guaranteed; RAM
content before the program starts is not preserved; a reset is refused while a watchpoint is active.

## Example

```python
result = target.reset()
target.check("halted after reset", result["outcome"], "halted")
target.reach("main")
```

A backend command failure is reported as an operation failure that keeps the cause and the
invalidation steps; the link survives it.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
