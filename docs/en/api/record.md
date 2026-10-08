# record

[API](index.md) · [Русский](../../ru/api/record.md)

`record(name, data) -> None`

| Property | Value |
| --- | --- |
| Module support | 0.2.0.dev0 → 0.2.0rc1 |
| API specification contract | 0.2.0; §4.9 |
| API_VERSION | 1 |
| Basis | the effective 0.1.0/0.2.0 contract and the scenarios of the verification firmware `tests/firmware` |

Implemented extension; `0.2.0rc1` is a local candidate, not a published stable release.

## Purpose

Appends a deep copy of data to the current scenario invocation journal. name is an exact nonempty str; names may repeat.

## Contract and limitations

Accepts exact None/bool/int, finite float, Unicode str, list and dict with string keys. Rejects tuple, bytes, subclasses, GDB objects, cycles and NaN/Inf. RecordError consumes no sequence/budget. No MCU reads, export or test-outcome changes.

Configure limits in api.toml `[records]`. Integers from 1 to the maximum, excluding bool:

| Parameter | Default | Maximum |
| --- | ---: | ---: |
| max_records | 128 | 1024 |
| max_nodes | 4096 | 32768 |
| max_text_bytes | 65536 | 524288 |
| max_depth | 8 | 32 |
| max_integer_bits | 256 | 1024 |

Record, node and UTF-8 byte budgets cover the entire journal. data depth starts at 0;
integer_bits uses int.bit_length. Nodes include names, keys, values and containers;
bytes include names, keys and strings. The wrapper is excluded. These are not RSS
or caller-retained-copy limits.

`t.record(name, t.profile)` records a snapshot of the run profile (`profile.snapshot()`).

## Example

```python
t.record("adc.sample", {"vdda_mv": t.value("board_adc_reading.vdda_mv")})
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.9.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/firmware/common/tests/board/test_measurements.py).
- [records](records.md), [record_error](record-error.md), [profile](profile.md).

Opt-in runner persistence: [description](../API.md#result-journal-capture-unreleased). The method contract is unchanged.

Record data is arbitrary; name does not define a measurement type. [Generic export and separate projections](../RESULTS.md).
