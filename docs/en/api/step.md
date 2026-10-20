# step

[API](index.md) · [Русский](../../ru/api/step.md)

`step(count=1, *, unit="source", mode="into") -> dict`

**Available since:** 0.3.0 · **API 3 (0.5.0):** in `async def` use `await t.step(…)`, in `def` the synchronous form is unchanged; a condition is evaluated without function calls. [Sync/async rules](../LIVE_EXECUTION.md).

## Purpose

Performs the given number of steps by source line or by instruction.

## Contract and limitations

The result describes the reached location and the frame-completion flag. On GDB 15+ a step is confirmed by the `end-stepping-range` reason; GDB 14 gives none, so a step is counted by the changed program counter and marked `inferred`.

Limitations: source stepping requires debug information; with `mode="over"` a call runs to
completion; instruction stepping does not preserve flag state between stops on some cores, so flag-
derived values are unsuitable as assertions.

## Example

```python
t.step(3)
t.check("stepped frames", len(t.frames()["frames"]) > 0, True)
```

An unavailable step mode fails with the requested mode named.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md).
