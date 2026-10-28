# write

[API](index.md) · [Русский](../../ru/api/write.md)

> **MMIO:** Even verify=False retains the before read. Single RHS evaluation does not remove repeated LHS evaluation or possible bitfield RMW. MMIO outside scope has no confirming readback; this does not make WO/FIFO/read-to-clear writes safe. [Limitations and model/board validation](../MMIO.md).

`write(path, value, *, verify=True) -> dict`; `write(rows, *, verify=True) -> list[dict]`

**Available since:** 0.3.0 · **API 3 (0.5.0):** unchanged, no `await`; the expression cannot call target functions (`expression_call_forbidden`).

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
`&`, `~`, `<<`, `>>`, `+`, `-`, comparisons) and firmware macros, for ordinary software data; use the dedicated contract for MMIO. A line break, `;` and assignments (`=`, `|=`, `<<=`, `++`, `--`) are refused: invalid syntax produces `unsupported_value`. Function calls are forbidden
(`expression_call_forbidden`); completed assignments appear in `mutations`.

`write(rows)` with a single list argument performs the `(path, value)` writes in order and returns the
list of results. The structure of every row is validated before the first write; a refused row stops
the rest, and writes already done are not undone. `verify` applies to every row.

```python
# Ordinary SRAM only; not peripheral registers.
t.write([
    ("input_state.source", 0),
    ("input_state.level", 1)
])
```

## Example

```python
t.write("app_state.ticks", 41)
t.write("app_delay", 100)
```

A target may ignore a read-only register write without a transport error. Command success
does not prove its effect; an SVD override does not make hardware writable.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md); expressions and the table of writes: items 4.6.2, 4.6.3.

## RHS evaluated once (0.5.0)

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

Compact result storage and console control do not remove checks; see [result journal](../API.md#result-journal-and-output-060-candidate-a22).


## Application and consumption are separate checks

SRAM readback confirms the write, but normal code can overwrite it before use.
Continue to processing and check the consumed value and branch. Include a baseline,
the next input and restoration of all changed resources. [Executable A5.1](../../../tests/controlled-input/README.en.md)
preserves a too-early write as an intentional FAIL. This is software-input
substitution, not GPIO or physical signal verification.
