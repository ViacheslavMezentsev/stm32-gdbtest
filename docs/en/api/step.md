# step

[API](index.md) · [Русский](../../ru/api/step.md)

`step(count=1, *, unit="source", mode="into") -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.2.9 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Performs the given number of steps by source line or by instruction.

## Contract and limitations

The result describes the reached location and the frame-completion flag. On GDB 15+ a step is confirmed by the `end-stepping-range` reason; GDB 14 gives none, so a step is counted by the changed program counter and marked `inferred`.

Limitations: source stepping requires debug information; with `mode="over"` a call runs to
completion; instruction stepping does not preserve flag state between stops on some cores, so flag-
derived values are unsuitable as assertions.

## Example

```python
target.step(3)
target.check("stepped frames", len(target.frames()["frames"]) > 0, True)
```

An unavailable step mode fails with the requested mode named.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
