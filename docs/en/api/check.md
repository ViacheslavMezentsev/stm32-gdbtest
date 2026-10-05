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
| `check(name, actual, matches(pattern))` | a Python regular expression is found in the text `actual` | `{"matches": pattern}`, `kind="matches"` |
| `check(name, actual)` | `actual` is true | `True`, `kind="truth"` |
| `check(rows)` | every row of the table passes, in order | one entry per row |

A list or tuple as `expected` is compared for equality as before: an array from `read` stays an
array. A table row is `(name, actual, expected)` or `(name, actual)`; string `actual` and `expected`
cells are evaluated as GDB expressions through `evaluate`, and `expected` may be a matcher. The
structure of every row is validated before the first evaluation; the first mismatch stops the table.

A mismatch raises `CheckFailed`. An argument error (empty name, invalid matcher bounds, empty table)
raises `ApiError` of operation `check` without a report entry. Values must be JSON-compatible.

## Where a string is a GDB expression and where it is a Python value

There is one rule: **GDB evaluates a string only where the data comes from the target.** These are the
parameters named `expression` and `path` (`read`, `evaluate`, `write`, `reach`, `until`…) and the cells of
the `check(rows)` table, which exists to verify the target state. The arguments of a single
`check(name, actual, expected)` are Python values, like the result of any other API operation.

| Form | The string `"SET"` as the expectation | Why |
| :--- | :--- | :--- |
| `check(name, actual, expected)` | compared as text | it receives operation results: frame names, error codes, stop kinds, values from `profile`; these are Python text, and so it has been since the first published tag |
| `check(rows)` | evaluated by GDB (the `SET` enum or macro → `1`) | the table replaced the "name, expression, expectation" helper: it reads registers and variables, and expectations are firmware identifiers |

So the same string behaves differently on purpose. If a single `check` evaluated strings as well,
comparisons such as `check("stop", stop["kind"], "breakpoint")` or
`check("code", error.details["code"], "unsupported_argument")` would go to GDB as symbols and fail, and
Python text would need a separate literal wrapper.

A one-line check of a pin with firmware macros has two equivalent spellings:

```python
# A one-row table: GDB evaluates both strings.
t.check([("PA5 high", "(GPIOA->ODR & GPIO_ODR_5) != 0", "SET")])

# A single check: the expressions are evaluated explicitly through evaluate.
t.check("PA5 high", t.evaluate("(GPIOA->ODR & GPIO_ODR_5) != 0"), t.evaluate("SET"))
```

The bit is normalized with `!= 0`: `GPIOA->ODR & GPIO_ODR_5` gives `0x20`, while `SET` is 1. `SET`/`RESET`
may be enums (`FlagStatus` in CMSIS, `GPIO_PinState` in HAL) or `-g3` macros — GDB evaluates both kinds if
the symbol is in the debug information of the ELF (an enum gets there when the firmware uses the type).

Common mistakes:

| Spelling | What happens | Instead |
| :--- | :--- | :--- |
| `check("PA5", t.read("(GPIOA->ODR & GPIO_ODR_5) != 0"), "SET")` | `1 == "SET"` — a mismatch | `t.evaluate("SET")` or a table |
| `check([("case id", t.profile.case["id"], "HW_CI_PROFILE")])` | GDB looks up the symbol `HW_CI_PROFILE` — a cell error | `check("case id", t.profile.case["id"], "HW_CI_PROFILE")` |
| `check([("PA5", "GPIOA->ODR & GPIO_ODR_5", "SET")])` | `0x20 == 1` — a mismatch | `"... != 0"` or a two-cell row without `expected` |

## Rules of the `check(rows)` table

1. A table row is `(name, actual, expected)` or `(name, actual)`.
2. **A string cell is a GDB expression.** Strings in `actual` and `expected` are evaluated in the
   halted program through `evaluate`: variables, fields, registers, `-g3` macros, enums, C arithmetic.
   A Python string cannot be compared in a table: GDB looks up `"HW_CI_PROFILE"` as a symbol. Such
   values are checked with a plain `check(name, actual, expected)`.
3. Non-string cells (numbers, `bool`, lists, tuples) and matchers are used as they are.
4. A two-cell row passes when the expression is true; this suits GDB functions that return 1 or 0.
5. The structure of every row is validated before the first evaluation, rows run in order, the first
   mismatch stops the table. An evaluation error names the row and the cell.

Firmware strings are compared by GDB functions right in the table:

```python
t.check([
    ("version", '$_streq(app_info.version, "v1.2.0-ci")'),          # equal C strings
    ("board", '$_streq(app_info.board, "stm32-gdbtest-ci")'),        # a char * pointer
    ("version length", "$_strlen(app_info.version)", 9),
    ("RAM copy", "$_memeq(app_version_ram, app_info.version, 16)"),  # 16 equal bytes
    ("version prefix", r'$_regex(app_info.version, "^v1\\.")'),      # a GDB regular expression
])
```

To get the string itself in Python (and see it in the report), use `evaluate(path, as_type=str)` and
the `matches` matcher.

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

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.3.5, items 4.1.1–4.1.4.
- [Matchers](matchers.md), [read](read.md), [evaluate](evaluate.md).
