# refused

[API](index.md) · [Русский](../../ru/api/refused.md)

`with t.refused(code, *, name=None, **details) as refusal: ...`

**Available since:** 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`.

## Purpose

A check of an expected operation refusal: the body of the `with` block must end with an `ApiError` of
`code`. It replaces a five- or six-line `try/except ApiError/else` construct.

## Contract and limitations

- Extra keyword arguments (`effect="none"`, `stage="validation"`, `width=32`) are compared with
  `error.details` together with the code.
- The result is recorded as one check: `actual` holds the found detail values, `expected` the
  expected ones, `kind="refused"`; the default name is `refused: <code>`.
- A matching refusal is suppressed and kept in `refusal.error` (`refusal.details` are its details) to
  check the cause or the journal after the block.
- If the body completes without an exception, the check fails with `actual=None`.
- A refusal with another code or details is a `CheckFailed` mismatch.
- `CheckFailed` and exceptions that are not `ApiError` pass out of the block unchanged.

## Example

```python
with t.refused("unsupported_argument", effect="none", name="an unsupported argument is refused"):
    t.call("app_step", object())

with t.refused("command_failed") as failure:
    t.evaluate("api030_no_such_symbol")
t.check("the cause is kept", failure.error.__cause__ is not None)

for path, code in (("api030_no_such_object", "invalid_path"), ("app_state.ticks + 1", "not_addressable")):
    with t.refused(code, stage="validation"):
        t.watch(path)
```

Before:

```python
try:
    t.call("app_step", object())
except ApiError as error:
    t.check("unsupported argument code", error.details["code"], "unsupported_argument")
    t.check("unsupported argument effect", error.details["effect"], "none")
else:
    t.check("an unsupported argument must be refused", False, True)
```

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), items 4.19.1–4.19.3.
- [api-error](api-error.md), [check](check.md).
