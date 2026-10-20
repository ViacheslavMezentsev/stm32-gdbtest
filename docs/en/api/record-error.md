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
