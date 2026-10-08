# evaluate

[API](index.md) · [Русский](../../ru/api/evaluate.md)

`evaluate(expression, *, as_type=None) -> int | float | bool | str`

| Property | Value |
| --- | --- |
| Module support | 0.3.0; char[] fix — Unreleased |
| API specification contract | §4.3, §4.18; char[] clarified in revision 0.3.8 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Evaluates an expression in the context of the halted program and returns the result of the requested
plain type.

## Contract and limitations

The conversion targets the requested type; an unsupported type or an expression error is reported as
an operation failure.

`as_type=str` (or `"str"`) reads a C string: a `char[N]` array up to the first zero or to the end of the
array, a `char *` pointer up to the zero, at most `STRING_LIMIT = 256` bytes. Bytes that are not UTF-8
are replaced with `�`; a string without a zero inside the limit is returned truncated and marked
`truncated` in `report["evaluations"]`. A NULL pointer raises `null_pointer`, an array of non-`char`
elements `unsupported_type`.

Limitations: the expression is evaluated on the current frame; side effects of the expression are
not rolled back; function calls inside an expression are outside the verified scope.

When GDB reports zero array size (for example, `extern const char name[]`), its address is read using
pointer rules: up to NUL or the 256-byte limit. A missing address gives `read_failed`. This fixes
ValueError on GDB 15/16 and false empty strings on GDB 14; known array bounds remain enforced.
An explicitly declared zero-length array follows the same rule.

## Example

```python
t.evaluate("app_state.ticks", as_type=int)
t.evaluate("app_state.led == 1", as_type=bool)
version = t.evaluate("app_info.version", as_type=str)   # "v1.2.0-ci" from char version[16]
board = t.evaluate("app_info.board", as_type=str)       # "stm32-gdbtest-ci" from const char *
t.check("version", version, matches(r"^v1\.\d+\.\d+"))
```

A GDB error while parsing or evaluating the expression is kept as the failure cause.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5; `as_type=str`: revision 0.3.5, items 4.18.1–4.18.2.
