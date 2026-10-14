# Scenario author checklist

[Documentation](index.md) → Scenarios · [Русский](../ru/SCENARIO_CHECKLIST.md)

A short review before a long run. Complements the [API reference](api/index.md),
[techniques](TESTING_TECHNIQUES.md) and [DDTT](DDTT.md); it does not establish board readiness.

## Before a run

1. Define expectations independently of the implementation and state the behavior being tested.
2. Check syntax, scenario discovery and requested [ELF contracts](CONTRACTS.md).
   `run --prepare-only` checks preparation without a board; it does not execute the hardware scenario body.
3. Check the selected ELF, configuration, tools and whether the stop location is reachable.
   A larger timeout does not repair an unreachable condition.
4. If later analysis requires records, enable `[results] capture = true` in session.toml.
   Define required record names, fields and observation counts beforehand.
5. Check each case's prerequisites before the main series. A separate rig PASS does not guarantee
   that its state remains suitable for all subsequent runs.

## Common mistakes

| Symptom | What to check | Contract |
| --- | --- | --- |
| Text is compared instead of a value | Scalar check treats strings as Python data; table string cells are evaluated by GDB | [check](api/check.md) |
| A set bit does not equal 1 | A mask differs from a boolean; compare the mask or normalize using != 0 | [Tables](TESTING_TECHNIQUES.md#tech-010) |
| Value conversion fails | Check declared type, expression and GDB version; pointers are not universally forbidden | [evaluate](api/evaluate.md), [read](api/read.md) |
| A method cannot be called | Check context, signature and available callable code; inline alone does not forbid a call | [C++](TESTING_TECHNIQUES.md#tech-019) |
| Snapshots match but are too short | Compare length with the expected debug-information size before modifying memory | [memory](api/memory.md) |
| An expression write has unexpected effects | Evaluation may occur when preparing verification and when writing; account for side effects or pass a previously computed number | [write](api/write.md) |
| A write is not verified | Inspect verified and verification scope; MMIO is not ordinary RAM | [write](api/write.md) |
| record rejects data | Dictionary keys must be strings; convert gdb.Value and bytes to supported Python values | [record](api/record.md) |
| Analysis finds no measurements | Distinguish disabled capture, an empty journal and a missing selection; none of these should be interpreted as a measured zero | [Results](RESULTS.md) |

## Before changing state

- Establish object lifetime, the current frame and side effects of called code.
- Verify backup completeness and suitability. An object copy does not automatically include
  pointed-to memory, external resources or peripheral state.
- Do not treat byte copying as universal C++ object restoration. MMIO requires device-specific
  semantics, including read and write side effects.
- Plan exception cleanup and separate diagnostics for restoration failure.
- Halting the CPU need not halt peripherals. Calling a function through GDB executes MCU code
  again; a pause, an inferior call and free execution are different experimental conditions.

## After a run

1. Separate the scenario verdict, artifact capture outcome and command outcome.
2. Check required evidence for completeness, ownership and integrity.
3. Preserve original FAIL/ERROR evidence and tested sources before editing the scenario.
4. Compare explicitly selected attempts and identify changed inputs and criteria.
5. Confirm cleanup and restoration. Unknown restoration is not PASS.
6. Record limits: injecting state tests a reaction, not whether the real event or task produces
   that state; an emulator PASS is not HW PASS.

## What automation can check

Existing tools check syntax, parameters and requested ELF contracts. Text-based hints cannot
replace semantic review and may be wrong. This page introduces no new automated checker.
Preflight is not a hardware test and does not prove that the scenario body is error-free.
