# write

[API](index.md) · [Русский](../../ru/api/write.md)

`write(path, value, *, verify=True) -> dict`; `write(rows, *, verify=True) -> list[dict]`

| Property | Value |
| --- | --- |
| Module support | 0.3.0.dev0 (core) |
| API specification contract | not accepted; designed revision 0.2.8 |
| API_VERSION | 1 (the effective contract does not change) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Writes a value into an addressable program object and returns the result with effect diagnostics. The value is an integer, a finite `float`, a `bool` (passed as 1/0) or a GDB expression (an enum constant, a macro); an expression is verified by what it evaluates to. Other values are refused before the write (`unsupported_value`).

## Contract and limitations

With verification (`verify=True`) a read-back confirms the applied value.

Limitations: addressable objects in RAM of a declared scalar type; integer widths are in the
verified scope, 64-bit and `float` are not. The read-back comparison runs only for objects in the
SRAM window: a peripheral register reads by its own rules, so the write still happens while the
reading and the `verify_scope=outside` marker are reported without claiming confirmation. A write failure is never hidden and is reported as an
operation failure; an already applied effect is not rolled back.

### An expression as the value and a table of writes

A string value is a C expression that GDB evaluates **before** the write: it may use operators (`|`,
`&`, `~`, `<<`, `>>`, `+`, `-`, comparisons) and firmware macros, so a read-modify-write of a register
is one line. A line break, `;` and assignments (`=`, `|=`, `<<=`, `++`, `--`) are refused: one write
changes exactly one object and appears in `mutations` (`unsupported_value`).

`write(rows)` with a single list argument performs the `(path, value)` writes in order and returns the
list of results. The structure of every row is validated before the first write; a refused row stops
the rest, and writes already done are not undone. `verify` applies to every row.

```python
# Start continuous conversions while the core is halted: the order of the rows matters.
t.write([
    ("ADC1->CFGR1", "ADC1->CFGR1 | ADC_CFGR1_CONT"),
    ("ADC1->CR", "ADC1->CR | ADC_CR_ADSTART"),
])
t.write("ADC1->CR2", "ADC1->CR2 & ~ADC_CR2_ADON")        # clear a bit with an expression
t.write([("SysTick->CTRL", control), ("NVIC->ISER[0]", enabled)])   # restore saved values
```

## Example

```python
t.write("app_state.ticks", 41)
t.write("app_delay", 100)
```

A write into an immutable area (Flash, read-only registers) ends with diagnostics, not with a silent
success.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), revision 0.2.5; expressions and the table of writes: revision 0.3.6, items 4.6.2, 4.6.3.
