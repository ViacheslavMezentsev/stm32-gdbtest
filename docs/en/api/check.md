# check

[API](index.md) · [Русский](../../ru/api/check.md)

`check(name, actual, expected=<truth>) -> None`; `check(rows) -> int`

| Property | Value |
| --- | --- |
| Module support | comparison: 0.1.0rc1 / v0.1.0-rc.1; matchers, truth check and table: 0.3.0.dev0 (core) |
| API specification contract | 0.1.0, item 4.1.1; revision 0.3.4, items 4.1.2–4.1.4 |
| API_VERSION | 1 |
| Basis | the verification firmware `tests/firmware`, every scenario |

## Purpose

Records one check in the report, prints PASS/FAIL and ends the scenario with FAIL on a mismatch.

## Contract and limitations

The arguments decide the kind of check:

| Call | Passes when | `expected` in the report |
| :--- | :--- | :--- |
| `check(name, actual, expected)` | `actual == expected` | the value |
| `check(name, actual, within(low, high))` | `low <= actual <= high` | `{"low", "high"}`, `kind="range"` |
| `check(name, actual, near(value, tolerance))` | `abs(actual - value) <= tolerance` | `{"value", "tolerance"}`, `kind="near"` |
| `check(name, actual, one_of(a, b, …))` | `actual` equals one of the options | `{"in": [...]}`, `kind="in"` |
| `check(name, actual)` | `actual` is true | `True`, `kind="truth"` |
| `check(rows)` | every row of the table passes, in order | one entry per row |

A list or tuple as `expected` is compared for equality as before: an array from `read` stays an
array. A table row is `(name, actual, expected)` or `(name, actual)`; string `actual` and `expected`
cells are evaluated as GDB expressions through `evaluate`, and `expected` may be a matcher. The
structure of every row is validated before the first evaluation; the first mismatch stops the table.

A mismatch raises `CheckFailed`. An argument error (empty name, invalid matcher bounds, empty table)
raises `ApiError` of operation `check` without a report entry. Values must be JSON-compatible.

## Example

```python
from stm32_gdbtest import case, near, one_of, within

t.check("initial count", t.read("board_adc_sequences"), 0)
t.check("VDDA, mV", t.read("board_adc_reading.vdda_mv"), within(2800, 3600))
t.check("die temperature, mdegC", t.read("board_adc_reading.temperature_mdeg_c"), near(30_000, 15_000))
t.check("stand backend", t.profile.stand["backend"], one_of("openocd", "jlink"))
t.check("GPIOA clock", t.read("RCC->AHBENR & RCC_AHBENR_GPIOAEN"))
t.check([
    ("PA5 output", "GPIOA->MODER & GPIO_MODER_MODER5", "GPIO_MODER_MODER5_0"),
    ("DMA channel", "DMA1_Channel1->CCR", "DMA_CCR_MINC | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_0 | DMA_CCR_TCIE | DMA_CCR_TEIE"),
    ("timer running", "TIM3->CR1 & TIM_CR1_CEN"),
])
```

An expectation that follows from the device (register bits, an interrupt number) is written with a
firmware identifier; physical quantities (frequencies, dividers, channel numbers) are set in the
scenario independently (TECH-001).

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.4, items 4.1.1–4.1.4.
- [Matchers](matchers.md), [read](read.md), [evaluate](evaluate.md).
