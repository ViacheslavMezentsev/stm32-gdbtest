# frames

[API](index.md) · [Русский](../../ru/api/frames.md)

`frames(limit=16) -> dict`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Returns the frame chain from the newest to the oldest with levels, function names and program
counters.

## Contract and limitations

It returns the frame list and a termination flag.

Limitations: `limit` bounds the walk; without debug information names may be missing and the walk
may end early; inlined functions may be absent as separate frames.

## Example

```python
chain = target.frames(limit=8)
target.check("top frame", chain["frames"][0]["function"], "app_step")
```

An incomplete walk is reported through the termination flag, not as an error.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
