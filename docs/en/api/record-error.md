# RecordError

[API](index.md) · [Русский](../../ru/api/record-error.md)

`RecordError(ValueError)`

**Available since:** 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`.

## Purpose

Public record/records validation exception; importable from stm32_gdbtest without GDB. code and limit describe the failure category.

## Contract and limitations

code: invalid_name, unsupported_type, invalid_text, non_finite, cycle, limit_exceeded. For limit_exceeded, limit is records/nodes/depth/text_bytes/integer_bits; otherwise None. Message and error precedence are not fixed. Unhandled exceptions produce ERROR; MemoryError is not replaced.

## Example

```python
from stm32_gdbtest import RecordError

try:
    t.record("", 1)
except RecordError as error:
    t.check("invalid name rejected", error.code, "invalid_name")
else:
    t.check("invalid name accepted", True, False)
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §5.6.
- [Implementation](../../../stm32_gdbtest/records.py).
- [Scenario or implementation check](../../../tests/host/test_record_errors.py).
- [record](record.md), [records](records.md).

## Limit diagnostics (0.6.0)

For `limit_exceeded`, `details` includes `record_name` (up to 128 characters),
`path` (up to 256), `maximum`, `used`, `attempted`, `attempted_lower_bound`.
Paths start with `$name` or `$data`; key labels are shortened. `used` is the committed
cumulative records/nodes/text_bytes budget; it is 0 for per-value depth/integer limits.
`attempted` describes the first excess, not the full rejected object's size.
An early text check may report a UTF-8 lower bound, explicitly marked by the flag.
Failure consumes no budget. Match structured fields, not traceback message text.

A2.1: compact storage may report `$definition`/`$definitions` paths.
A `records()` expansion failure has `details.operation="records"` and
`details.scope="materialization"`; it does not discard the journal.

## A3.2 (0.6.0)

`records()` adds `incomplete_evidence` for incomplete journals and `invalid_argument` for non-bool require_complete. Explicit journal truncation suppresses only cumulative records/nodes/text_bytes exhaustion; other errors remain errors. Full contract and formats: [Journaling](../JOURNALING.md#explicit-journal-truncation).
