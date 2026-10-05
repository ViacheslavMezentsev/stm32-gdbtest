# until

[API](index.md) · [Русский](../../ru/api/until.md)

`until(location=None) -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.2.9 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Runs the program to the given location in the current frame without stopping at intermediate lines.

## Contract and limitations

Without an argument it acts as leaving the current line. With a location, `reached` is reported only when
the stop is at an address of that location (`targets`); when the current frame returns first the outcome is
`frame_exited` (GDB 16 calls such a stop `location-reached` too, so the address decides). GDB 14 passes no stop
reason: the kind is derived from the address and the frame and marked `inferred`.

Limitations: the location must be inside the current frame; passing through a call depends on the
debugger; an unreachable location ends with the scenario timeout.

## Example

```python
t.until("app_loop")
t.check("line reached", t.frames()["frames"][0]["function"], "app_loop")
```

Leaving the frame bounds is reported as a failure, not as a silent continuation.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
