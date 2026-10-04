# evaluate

[API](index.md) · [Русский](../../ru/api/evaluate.md)

`evaluate(expression, *, as_type=None) -> int | float | bool`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.3.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Evaluates an expression in the context of the halted program and returns the result of the requested
plain type.

## Contract and limitations

The conversion targets the requested type; an unsupported type or an expression error is reported as
an operation failure.

Limitations: the expression is evaluated on the current frame; side effects of the expression are
not rolled back; function calls inside an expression are outside the verified scope.

## Example

```python
target.evaluate("app_state.ticks", as_type=int)
target.evaluate("app_state.led == 1", as_type=bool)
```

A GDB error while parsing or evaluating the expression is kept as the failure cause.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
