# reset

[API](index.md) · [Русский](../../ru/api/reset.md)

`reset() -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | 0.3.0; dialect selection clarified in 0.3.14 |
| API_VERSION | 2 in candidate v0.4.0 |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Resets the target through the backend command, leaves the core halted and invalidates debugger
caches.

## Contract and limitations

An active scenario breakpoint or watchpoint raises `active_points` before reset; remove it explicitly.
After the command the register and frame
caches are invalidated, including after a failed attempt; the result describes the state and the
invalidation steps.

Command source: the backend dialect. OpenOCD resets with `monitor reset halt`, ST-LINK GDB Server and
J-Link with `monitor reset`; the section of the target profile for the selected server (schema 2) or the
session override `STM32_GDBTEST_RESET_COMMAND` change the value. It is resolved once when the run is
prepared and used by both the boot sequence and `reset()`; a scenario reads it as `stand.reset_command`.
The old `api.toml` key `reset.command` is now file data only and never affects execution. Schema 1 commands apply only to OpenOCD. Overrides do not change teardown or recovery. After a failed attempt the caches are invalidated, there is no automatic retry, and frames and registers stay invalid until a new `reach`.

Limitations: the reset command belongs to the backend (`monitor reset halt` for OpenOCD,
`monitor reset` for ST-LINK GDB Server and J-Link); a stop before the program's first instruction is not guaranteed; RAM
content before the program starts is not preserved; a reset is refused while a watchpoint is active.

## Example

```python
result = t.reset()
t.check("halted after reset", result["outcome"], "halted")
t.reach("main")
```

A backend command failure is reported as an operation failure that keeps the cause and the
invalidation steps; link state after a failure is not guaranteed.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.14.

Since v0.4.0, backend `st-util` uses `monitor reset`; the optional `[st-util]` section belongs to schema 2. The method contract is unchanged.
