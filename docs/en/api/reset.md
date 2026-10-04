# reset

[API](index.md) · [Русский](../../ru/api/reset.md)

`reset() -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.3.0 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Resets the target through the backend command, leaves the core halted and invalidates debugger
caches.

## Contract and limitations

Before the reset the scenario's active points are removed; after the command the register and frame
caches are invalidated, including after a failed attempt; the result describes the state and the
invalidation steps.

Command source: the `reset.command` key in `api.toml`; it defaults to the backend value (OpenOCD uses the profile's `reset_halt`, J-Link uses `monitor reset`) and a session may override it. After a failed attempt the caches are invalidated, there is no automatic retry, and frames and registers stay invalid until a new `reach`.

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
