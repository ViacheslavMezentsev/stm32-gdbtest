# resume

[API](index.md) · [Русский](../../ru/api/resume.md)

`resume() -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.2.9 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Continues execution and returns the result describing the stop reason.

## Contract and limitations

Movement continues to a point, a watch event or termination; the result distinguishes a software
point, a watch event and termination.

Limitations: `resume()` does not promise an unbounded wait — the scenario timeout applies above it;
with several active points the stop reason is the first event.

## Example

```python
t.resume()
t.check("stopped by a breakpoint", t.stops()[0]["kind"], "breakpoint")
```

Exceeding the scenario timeout ends the run instead of hanging in a wait.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
