# Scenario author checklist

[Documentation](index.md) → Scenarios · [Русский](../ru/SCENARIO_CHECKLIST.md)


For an observer, separately check window completion, SRAM/IRQ ownership, removal before restoring bytes, and an original repeat after removal. [Example and limits](LIVE_OBSERVER.md).
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
| An expression write has unexpected effects | API 3 evaluates RHS once; LHS must be stable and hidden function calls are forbidden | [write](api/write.md) |
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

## Before moving from a sandbox to hardware

- Separate the host fake, emulator and board: each checks a different claim.
- For C++, check completed construction, object lifetime, the owning frame, callable method
  code and the size of the argument buffer owned by the example.
- Establish whether the call can wait for an interrupt, delay or occupied resource.
- Check data, counters and unchanged neighbors independently of a bool/success flag.
- Record properties the model does not reproduce; do not extend its PASS to those properties.
- In a separate negative run, supply an incorrect expectation: obtain FAIL and artifacts.
  Check preparation failure separately: it is ERROR, not a refusal by the tested function.
- Confirm owned-process cleanup and port release after errors; do not kill unrelated
  processes by name or discard original FAIL/ERROR evidence.

See the [DDTT route](DDTT.md#sandbox-route) and [TECH-020](TESTING_TECHNIQUES.md#tech-020)
for persistence effects. These checks do not replace agreement on the hardware experiment.

## After a run

1. Separate the scenario verdict, artifact capture outcome and command outcome.
2. Check required evidence for completeness, ownership and integrity.
3. Preserve original FAIL/ERROR evidence and tested sources before editing the scenario.
4. Compare explicitly selected attempts and identify changed inputs and criteria.
5. Confirm cleanup and restoration. Unknown restoration is not PASS.
6. Record limits: injecting state tests a reaction, not whether the real event or task produces
   that state; an emulator PASS is not HW PASS.

## Evidence review questions

- Is snapshot size independently established and length checked before writing? Was `sizeof` converted to bool?
- API 3: RHS is evaluated once; LHS must be stable and hidden calls are forbidden.
- Is preflight PASS being confused with a valid `call()` name or object readiness?
- Were record names, counts, fields, types and units checked before numeric analysis? Empty `all()` is not evidence.
- Are body failure, capture outcome, analysis verdict and restoration retained separately?
- Did the experiment stop on restoration failure without hiding the original error behind successful cleanup?

Examples: [tables and writes](TESTING_TECHNIQUES.md#tech-010),
[records](TESTING_TECHNIQUES.md#tech-011), [C++ and snapshots](TESTING_TECHNIQUES.md#tech-019).


## What automation can check

Existing tools check syntax, parameters and requested ELF contracts. Text-based hints cannot
replace semantic review and may be wrong. This page introduces no new automated checker.
Preflight is not a hardware test and does not prove that the scenario body is error-free.

For a C++ contract, inspect DWARF for `this`: `T * const` and `const T *` differ.
API 3 (0.5.0) supports pointer qualifiers; see [details](CONTRACTS.md).

## Before accessing MMIO

- Establish register semantics: RO/WO/RW, W1C, read-to-clear, FIFO; allowed width and order.
- For ordinary write, check hidden accesses: before remains with verify=False; check tables evaluate strings; bitfields may cause RMW.
- Disable unrelated IDE register refresh during measurement. Halt does not freeze DMA.
- Run Renode with an access log, then the same segment on an authorized target board/backend.
- Define semantic recovery, not generic snapshot restoration; do not retry blindly after errors.

[MMIO limitations and skill](MMIO.md). For 0.5.0 use [mmio.read/write](api/mmio.md); SVD and ACK do not establish physical effects.


Live windows in 0.5.0: ordinary scenarios remain supported; `async def`,
`resume(sync=False)`, `await wait()` and `await halt()` — [contract and migration](LIVE_EXECUTION.md).


## Before a stateful, timed or externally captured series

- Does the next operation after failure run without reset, with different data and length?
  Are both callback orders and ring wrap covered? [TECH-021](TESTING_TECHNIQUES.md#tech-021).
- Is virtual tick separated from physical delay? Are before/at/after threshold, wrap and
  the maximum interval checked? [TECH-022](TESTING_TECHNIQUES.md#tech-022).
- Are driver and DMA states consistent, including the other direction? Does SVD match
  the MCU, without treating W1C/FIFO recovery as RAM restoration? [TECH-023](TESTING_TECHNIQUES.md#tech-023).
- Are counter frequency/mode, overhead and absence of missed wraps established?
  Is the measured maximum distinguished from WCET? [TECH-024](TESTING_TECHNIQUES.md#tech-024).
- Is freshness established by publication sequence, not just tick? Are steady noise,
  transients and outliers separate experiments? [TECH-025](TESTING_TECHNIQUES.md#tech-025).
- Is the receiver ready before resume, with owned processes, deadline and partial-startup
  cleanup? Are source, units, clocks and gaps known? [TECH-026](TESTING_TECHNIQUES.md#tech-026).
- Is the C++ method checked against ELF and current API? Passing preflight does not permit
  `Class::method` in `Target.call()`; parsing `execute("call ...")` text is not a portable
  contract. Do not hide calls in read/write expressions.
- Does restoration cover objects, pointed-to memory, arguments, clocks, peripherals and
  external sources according to actual interventions? Is irreversible output accounted for?

These are manual review questions; current automated checks do not establish these properties.

## Logical time and call results

- Compare return_value, not the call dictionary; verify outcome and return_state.
- Separate model ticks from API timeout and host time; no hidden calls in read.
- Cover threshold −1/exact/+1, wrap and a fresh epoch after failure without reset.
- Define counter width, allowed interval and the no-missed-full-wrap condition.
- Distinguish application return codes from API refusals (refused).

[Executable example](../../tests/logical-time/README.en.md).

## Counters and observation cost

- Independent increment bound strictly below one full wrap?
- Completeness, epoch and valid checked before interpreting zero?
- Empty baseline distinguished from total observer cost?
- All samples retained with predeclared warmup, units and measurement scope?
- Sample maximum is not WCET; host time is not MCU cycles?

[Example](../../tests/counter-cost/README.en.md).
