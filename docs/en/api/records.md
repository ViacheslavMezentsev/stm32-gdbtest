# records

[API](index.md) · [Русский](../../ru/api/records.md)

`records(name=None) -> list[dict]`

| Property | Value |
| --- | --- |
| Module support | 0.2.0.dev0 → 0.2.0rc1 |
| API specification contract | 0.2.0; §4.10 |
| API_VERSION | 1 |
| Basis | the effective 0.1.0/0.2.0 contract and the scenarios of the verification firmware `tests/firmware` |

Implemented extension; `0.2.0rc1` is a local candidate, not a published stable release.

## Purpose

Returns independent mutable copies with sequence/name/data keys. None selects all; a nonempty str filters by exact name; no matches returns [].

## Contract and limitations

Insertion order and sequence starting at 1 survive filtering. Mutating copies does not change the journal. clear/reset/continue do not clear it within an invocation. Invalid filters raise RecordError. Each call copies its selection.

## Example

```python
from statistics import mean, stdev

samples = [row["data"]["vdda_mv"] for row in t.records("adc.sample")]
t.check("enough samples", len(samples) >= 2, True)
summary = {"mean": mean(samples), "stdev": stdev(samples)}
last_two = samples[-2:]
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

Requires at least two previously collected adc.sample records; stdev uses N−1.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.10.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../tests/firmware/common/tests/board/test_measurements.py).
- [record](record.md), [record_error](record-error.md).

Opt-in runner persistence: [description](../API.md#result-journal-capture-unreleased). The method contract is unchanged.
