# ApiError

[API](index.md) · [Русский](../../ru/api/api-error.md)

`ApiError(Exception): error.details; error.code; error.__cause__`

**Available since:** 0.3.0 · **API 3 (0.5.0):** new codes `unawaited_operation`, `already_awaited`, `operation_timeout`, `halt_timeout`, `expression_call_forbidden`, `unsupported_async_command`, `call_incomplete`.

## Purpose

Describes an API operation failure separately: what was attempted (`operation`), at which stage
(`stage`), with which observed effect (`effect`) and why (`code`). The original debugger error is kept
as the cause.

## Contract and limitations

`details` always carries `operation`, `stage`, `effect` and `code`; extra operation fields are merged
into the same dictionary. `code` is also available as a property.

Limitations: the operation vocabulary is closed (`read`, `write`, `eval`, `registers`, `frames`,
`breakpoint`, `watch`, `resume`, `reach`, `step`, `until`, `finish`, `ret`, `call`, `reset`, `execute`,
`record`, `records`, `config`, `mmio.read`, `mmio.write`); stages are `validation`, `command`, `observe`, `readback`, `transport`, `audit`; effects are
`none`, `unknown`, `partial`, `applied`. `effect` reports only the observed effect and a failure does
not roll back what already happened. The full code set is formed as the methods are implemented.

## Example

```python
try:
    t.ret(1 << 40)
except ApiError as error:
    t.check("operation", error.details["operation"], "ret")
    t.check("effect is known or unknown", error.details["effect"] in ("none", "unknown"), True)
```

An operation failure differs from a check mismatch: the former is `ApiError`, the latter is
`CheckFailed`.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md).

[MMIOError](mmio.md) defines the effect=none/unknown boundary and journal failures.
