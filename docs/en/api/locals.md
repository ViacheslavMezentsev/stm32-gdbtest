# locals

[API](index.md) · [Русский](../../ru/api/locals.md)

`locals(frame=None) -> dict; arguments(frame=None) -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | revision 0.3.3 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the verification firmware `tests/firmware`, scenarios HW_CI_RETURN_VALUE, HW_CI_STEP_SOURCE |

## Purpose

Local variables and arguments of a frame as one dictionary.

## Contract and limitations

Returns `{"operation", "function", "values", "unavailable"}`. `frame` is `None` (the innermost
frame), an `int` depth counted from it, or a GDB frame object. `locals` walks the blocks from the inner
one to the function block, an inner name shadows an outer one; arguments are not part of `locals`.
Optimized-out and unconvertible values are listed in `unavailable` instead of raising. A frame without
debug information raises `no_debug_info`, a missing frame `no_frame`.

## Example

```python
target.reach("app_step")
arguments = target.arguments()["values"]
target.check("mode argument", arguments["mode"], target.evaluate("APP_MODE_BLINK"))
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.3, items 4.17.1, 4.17.2.
