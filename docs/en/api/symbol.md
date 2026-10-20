# symbol

[API](index.md) · [Русский](../../ru/api/symbol.md)

`symbol(name) -> dict`

**Available since:** 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`.

## Purpose

Address, size, type and section of a global or static symbol without manual `&x` and `sizeof`.

## Contract and limitations

Returns `{"operation": "symbol", "name", "kind", "address", "size", "type", "section"}`.
`kind` is `variable` or `function`; a function size is the length of its lexical block (or `None`),
a variable size is the `sizeof` of its type. `section` comes from `info symbol` and may be `None`.
Only global and static symbols are looked up; frame variables are read by `locals`. A missing symbol
raises `ApiError` (`symbol_absent`).

## Example

```python
state = t.symbol("app_state")
t.check("app_state in .bss", state["section"], ".bss")
t.check("app_state size", state["size"], t.evaluate("sizeof(app_state)"))
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), items 4.15.1.
