# write

[API](index.md) · [Русский](../../ru/api/write.md)

> **MMIO:** Even verify=False retains the before read. Single RHS evaluation does not remove repeated LHS evaluation or possible bitfield RMW. MMIO outside scope has no confirming readback; this does not make WO/FIFO/read-to-clear writes safe. [Limitations and model/board validation](../MMIO.md).

`write(path, value, *, verify=True) -> dict`; `write(rows, *, verify=True) -> list[dict]`

| Property | Value |
| --- | --- |
| Module support | 0.3.0; refined in the 0.4.2 candidate |
| API specification contract | accepted, revision 0.3.17 |
| API_VERSION | 2 (signatures unchanged) |
| Basis | the agreed verification firmware `tests/firmware` and its scenarios (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Purpose

Writes a value into an addressable program object and returns the result with effect diagnostics. The value is an integer, a finite `float`, a `bool` (passed as 1/0) or a GDB expression (an enum constant, a macro); an expression is verified by what it evaluates to. Other values are refused before the write (`unsupported_value`).

## Contract and limitations

With verification (`verify=True`) a read-back confirms the applied value.

Limitations: addressable objects in RAM of a declared scalar type; integer widths, 64-bit values, `float`, bool, enum and pointers were
checked on a neutral ELF in Renode, not newly accepted on hardware. The read-back comparison runs only for objects in the
SRAM window: a peripheral register reads by its own rules, so the write still happens while the
reading and the `verify_scope=outside` marker are reported without claiming confirmation. A write failure is never hidden and is reported as an
operation failure; an already applied effect is not rolled back.

### An expression as the value and a table of writes

A string value is a C expression that GDB evaluates **before** the write: it may use operators (`|`,
`&`, `~`, `<<`, `>>`, `+`, `-`, comparisons) and firmware macros, so a read-modify-write of a register
is one line. A line break, `;` and assignments (`=`, `|=`, `<<=`, `++`, `--`) are refused: the destination assignment
appears in `mutations`, but an RHS function can change other objects (`unsupported_value`).

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

## 0.4.2 refinement and migration

A successful assignment evaluates the RHS once regardless of `verify`, including table rows.
Verification uses GDB's assignment result converted to the destination type: for example,
257 assigned to uint8_t is verified as 1. Values are not universally converted through Python int.
Version 0.4.1 could evaluate string RHS twice with verify=True; this behavior is corrected.
Explicit evaluate → ready value → write remains a supported portable technique.

`path` must identify a stable object without side effects: reads and address inspection precede
assignment, followed by readback in SRAM. LHS evaluation is not limited to once; atomicity,
volatile stability and MMIO safety are not guaranteed. MMIO retains verify_scope=outside,
without a confirming post-write read.

Command errors: command_failed / command / unknown (RHS may already have changed state).
Post-write read failures: read_failed / readback / applied; mutations retains after=None.
Assignment-result conversion failures: conversion_failed / readback / applied.
Readback mismatches retain verification_failed. No retries or rollback.
