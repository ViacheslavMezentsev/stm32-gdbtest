# symbol

[API](index.md) · [Русский](../../ru/api/symbol.md)

`symbol(name) -> dict`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | revision 0.3.3 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the verification firmware `tests/firmware`, scenarios HW_CI_PROFILE, HW_CI_POINT_BUDGET |

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

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.3, items 4.15.1.
