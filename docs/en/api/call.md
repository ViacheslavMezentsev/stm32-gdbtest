# call

[API](index.md) · [Русский](../../ru/api/call.md)

`call(function, *args) -> dict`

| Property | Value |
| --- | --- |
| Module support | not released: 0.3.0 package design |
| API specification contract | not accepted; designed revision 0.2.5 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Calls a debugged program's function on the halted core and returns the call result.

## Contract and limitations

Arguments are passed by value; the result describes the returned value and its availability.

Limitations: the call runs on the halted core and changes its state — the function's side effects
are kept; a long call is bounded by the scenario timeout; pointers, floating-point numbers and
variadic arguments are outside the verified scope.

## Example

```python
result = target.call("app_step")
target.check("call returned a value", result["return_state"], "available")
```

An error inside the called function is reported as an operation failure, not as a debugger
exception.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5.
