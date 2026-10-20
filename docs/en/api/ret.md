# ret

[API](index.md) · [Русский](../../ru/api/ret.md)

`ret(value=None) -> dict`

**Available since:** 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`.

## Purpose

Returns control early from the current function, substituting a value of the declared return type, and
describes the result.

## Contract and limitations

The value is encoded by the declared return type: the command is built as `return (<type>)0x<value>`,
and the result reports `operation`, `function`, `caller`, `supplied`, `applied`, `command` and
`type_name`. A value outside the declared width is refused with `out_of_range` before the command runs,
carrying `low`, `high` and `width`; a logical type is bounded to 0 and 1. An empty call issues the plain
`return`; a string is passed through as a GDB expression.

Limitations: the rest of the function is skipped and completed effects are not rolled back; width and
signedness come from the declared type (a typedef without the word `unsigned` is classified by its type
name); the caller decides how the value is used; pointer, floating-point and struct return values are
outside the verified scope.

## Example

```python
t.reach("app_step")
result = t.ret(42)
t.check("the caller received the value", t.read("app_received.produced"), result["applied"])
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md).
