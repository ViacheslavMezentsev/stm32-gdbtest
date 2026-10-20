# locals

[API](index.md) · [Русский](../../ru/api/locals.md)

`locals(frame=None) -> dict; arguments(frame=None) -> dict`

**Available since:** 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`.

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
t.reach("app_step")
arguments = t.arguments()["values"]
t.check("mode argument", arguments["mode"], t.evaluate("APP_MODE_BLINK"))
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), items 4.17.1, 4.17.2.
