# RecordError

[API](index.md) · [Русский](../../ru/api/record-error.md)

`RecordError(ValueError)`

| Property | Value |
| --- | --- |
| Module support | 0.2.0.dev0 → 0.2.0rc1 |
| API specification contract | 0.2.0; public import clarified in 0.2.1; §5.6 |
| API_VERSION | 1 |
| Basis | the effective 0.1.0/0.2.0 contract and the scenarios of the verification firmware `tests/firmware` |
| Former-name alias | RecordError -> a subclass of ApiError (the alias works without warnings until 1.0; removal in 0.4.0) |

Implemented extension; `0.2.0rc1` is a local candidate, not a published stable release.

## Purpose

Public record/records validation exception; importable from stm32_gdbtest without GDB. code and limit describe the failure category.

## Contract and limitations

code: invalid_name, unsupported_type, invalid_text, non_finite, cycle, limit_exceeded. For limit_exceeded, limit is records/nodes/depth/text_bytes/integer_bits; otherwise None. Message and error precedence are not fixed. Unhandled exceptions produce ERROR; MemoryError is not replaced.

## Example

```python
from stm32_gdbtest import RecordError

try:
    target.record("", 1)
except RecordError as error:
    target.check("invalid name rejected", error.code, "invalid_name")
else:
    target.check("invalid name accepted", True, False)
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §5.6.
- [Implementation](../../../stm32_gdbtest/records.py).
- [Scenario or implementation check](../../../tests/host/test_record_errors.py).
- [record](record.md), [records](records.md).
