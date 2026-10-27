# Testing techniques catalogue

[Documentation](index.md) · [Русский](../ru/TESTING_TECHNIQUES.md)


A complete composition of techniques: [neutral live observation](LIVE_OBSERVER.md). Separate admission, complete snapshot, independent oracle, records before check, verified removal and repeat without reset; also covers C++/MMIO migration limits of older scenarios.
A practical companion to [test authoring](TEST_AUTHORING.md) and the [API reference](api/index.md).
The cards describe techniques from bundled scenarios and consumer practice: the shared ones
(`tests/firmware/common/tests`), the scenarios of the five CMSIS profiles (`tests/firmware/profiles`)
and the F030 HAL fixture (`tests/hal-f030`). These are method cards, not new specification
requirements, API operations or coverage metrics.

Before a run, use the [scenario checklist](SCENARIO_CHECKLIST.md).

Cards TECH-021–026 separately describe recommendations from consumer practice;
TECH-021 includes a neutral executable example; the others remain recommendations.

## Bundled scenario style

The host test [`tests/host/test_scenario_style.py`](../../tests/host/test_scenario_style.py) checks
these rules; `python tests/host/test_scenario_style.py` lists every finding by file.

**Layout**

- Module header: a concise purpose as `RU:` and `EN:` lines; all other comments are English.
- A purpose comment (not a docstring) precedes every function, above its decorator.
  Two blank lines separate top-level functions and follow the imports.
- One blank line separates meaningful blocks inside a function. A comment opens a block: a blank line
  goes above it unless it is the first line of a nested block. Check and write tables and nontrivial
  loops are explained by a comment directly above them.
- A line of up to 120 characters is not split: a statement that fits on one line is written on one line.
  Longer constructs are split at meaningful boundaries; a continuation aligns with the opening bracket
  or, when the bracket ends the line, is indented by four spaces.
- Optional trailing commas are not used. A one-element tuple keeps its comma: `labels=("adc",)`.
- A module constant is explained by a comment above it or above the group it continues.
  A constant of one case is declared in that case, a shared one in the module prologue.

**API**

- The Target object is called `t` in scenarios and examples. The former `value`, `fields`, `set_value`,
  `force_return` are not used: `read`/`evaluate`, `read(path, fields=…)`, `write`, `ret` replace them.
- Three or more consecutive checks of target values form a `t.check(rows)` table:
  `('name', 'GDB expression', expected)`. A string cell of the table is a GDB expression, a number
  and a matcher are Python values ([TECH-010](#tech-010)). Checks of Python values — results of API
  methods, strings, collections — stay separate `t.check(name, actual, expected)` calls: a Python string
  in a table cell would be evaluated by GDB as an expression.
- Expectations that follow from the device (register bits, IRQ numbers, addresses) are written as
  firmware identifiers; physical quantities (frequencies, dividers, channel numbers) as named scenario
  constants ([TECH-001](#tech-001)).
- An expected refusal is checked with `with t.refused(code, …)`, not with `try/except ApiError`
  ([TECH-012](#tech-012)).
- Use `t.mmio.read/write` with SVD for peripherals ([TECH-006](#tech-006)).
  RMW is appropriate only when reads and writes are allowed without unsafe effects;
  ordinary RAM values can be written using `t.write(rows)`.
- A stop location is named by a function (`reach`, `finish`, `until(function)`). A `file:line` location
  breaks with any edit of the source and is allowed only in the scenario that checks line locations
  themselves ([TECH-016](#tech-016)).

## Using this catalogue

`TECH-NNN` IDs are stable: never renumber or reuse them. Titles may change; anchors remain.
Mark an obsolete card and link its replacement. A scenario references a technique with a comment
next to a nontrivial action:

```python
# TECH-005: docs/ru/TESTING_TECHNIQUES.md#tech-005 (EN: docs/en/TESTING_TECHNIQUES.md#tech-005).
# Make the ready predicate impossible without touching the oscillator/backup domain.
t.write("mask", 0)
```

Paths are relative to the module root. In an external consumer, give the URL of the pinned module
version with the same anchor. `@case` and requirements keep their own IDs; TECH replaces neither the
ELF contract nor requirement traceability.

| Group | Techniques |
| --- | --- |
| ELF, build and observation | [001 macros](#tech-001), [002 address before a context change](#tech-002), [017 profile](#tech-017), [018 strings](#tech-018) |
| Asynchronous execution | [003 callback/IRQ](#tech-003), [013 who writes](#tech-013) |
| Controlled faults | [004 function return](#tech-004), [005 argument](#tech-005), [006 MMIO](#tech-006), [012 expected refusal](#tech-012) |
| Numerical checks | [007 vectors](#tech-007) |
| Sleep and interrupts | [008 WFI context](#tech-008) |
| HAL | [009 arguments and source variant](#tech-009) |
| Organizing checks | [010 tables](#tech-010), [014 call as a predicate](#tech-014) |
| Navigation | [015 choosing the stop](#tech-015), [016 stop location](#tech-016) |
| Measurement series | [011 collection and calculation](#tech-011) |
| C++ | [019 this, overloads, types](#tech-019) |
| Storage | [020 deferred writes](#tech-020) |
| Consumer practice | [021 events and next cycle](#tech-021), [022 state-machine time](#tech-022), [023 driver/DMA](#tech-023), [024 cost and counters](#tech-024), [025 filters](#tech-025), [026 external witness](#tech-026) |

Moving a card to another MCU, HAL, GCC or backend needs a new verification: the links point to code
and protocols, they do not promise the same result in every environment.

<a id="tech-001"></a>
## TECH-001 — Macros from the ELF and independent expectations

**Goal:** check the configuration through registers and firmware macros without repeating its calculation.

Stop in a function with the right macro context (`t.reach("board_led_toggle")` — the translation unit
that includes the device header) and check with a table. Bits, masks and IRQ numbers are written as
identifiers, so the expectation comes from the same header as the firmware:

```python
t.check([
    ("HSI enabled and ready", "RCC->CR & (RCC_CR_HSION | RCC_CR_HSIRDY)", "RCC_CR_HSION | RCC_CR_HSIRDY"),
    ("nominal core frequency", "SystemCoreClock", HSI_HZ),
    ("1 ms reload at nominal 8 MHz", "SysTick->LOAD", HSI_HZ // 1000 - 1)
])
```

Frequencies, dividers and physical channel numbers are independent scenario constants:
`HSI_HZ = 8_000_000` comes from the RM, not from `SystemCoreClock`. Compare a masked result with the
mask, not with 1. Do not define a missing macro to get a PASS: a macro absent from the ELF is a build
error (`-g3` in the right translation unit) or a contract error.

**Environment:** `-g3`, the right MCU and HAL defines; the ELF contract lists the macros and their
context. A definition in an installed header does not prove its presence in the ELF.
**Boundary:** a getter may read a FIFO or take part in an SR/DR sequence; a read with an effect needs
a recovery defined in advance. Clock enabled does not prove that a particular macro was called.
[HAL macro guidance](HAL_MACRO_GUIDE.md),
[clock/gpio F030](../../tests/firmware/profiles/f030r8/tests/board/test_ci.py).

<a id="tech-002"></a>
## TECH-002 — Saving an address before a DWARF context change

**Goal:** compare a register before and after moving into a function where its macros are not visible.

Where the context exists, save the address as a number and the mask as a value; after the move, read
through the address with an explicit type:

```python
icsr_address = t.evaluate("&SCB->ICSR", as_type=int)
active_mask = t.read("SCB_ICSR_VECTACTIVE_Msk")
t.reach("app_loop")
t.check("thread resumes", t.read(f"*(unsigned int*){icsr_address} & {active_mask}"), 0)
```

`memory()` does not fit here: it reads only the SRAM and flash of the profile and refuses peripheral
addresses. Do not replace the lost context with an arbitrary address constant.
**Environment:** the 32-bit STM32 memory map; the address is valid within the same session and ELF.
**Boundary:** this works around a lost macro context; it does not prove that reading the register is safe.
[RTC deadline: the original ERROR and the fix](F030_RTC_DEADLINE.md),
[rtc_alarm, rtc_deadline](../../tests/firmware/profiles/f030r8/tests/board/test_rtc.py).

<a id="tech-003"></a>
## TECH-003 — Callback/IRQ → published result

**Goal:** connect a natural event with the right exception and a change of the application state.

CMSIS: `t.reach("RTC_IRQHandler")`, a table of `SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk` against
`RTC_IRQn + 16`, the event flags, then the publication counter and the return to thread mode. A second
event confirms the re-arming. HAL: stop in the callback and compare the handle (`t.read("timer")` with
`t.read("&htim3")`), then wait for the publication in the application loop. The exception number is
`SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk`: the GDB names `xPSR`/`xpsr` depend on the server.

**Environment:** active IRQ/DMA, handler symbols; the HAL weak callback is overridden by the code under test.
**Boundary:** a peripheral may keep running while the core is halted; callback frequency under a
debugger does not measure performance; a software IRQ does not prove a physical edge. VECTACTIVE does
not clear flags and does not prove the physical IRQ source.
RTC is adapted per family: F103 uses counter/alarm with re-arming in the main thread, F4 a masked
calendar Alarm A; do not move the F030 dividers (LSI 40 kHz) to F4 (32 kHz).
[CMSIS RTC](F030_CMSIS_RTC.md), [RTC/Sleep F411](F411_CMSIS_RTC_SLEEP.md),
[rtc_alarm](../../tests/firmware/profiles/f030r8/tests/board/test_rtc.py),
[HAL power](../../tests/hal-f030/hal_scenarios/power.py).

<a id="tech-004"></a>
## TECH-004 — Forcing a function return

**Goal:** check how the caller reacts when the function body is skipped.

At the entry of a function, `t.ret(value)` finishes it with a typed value: the value is converted to
the declared return type, an identifier is evaluated by GDB (`t.ret("HAL_ERROR")`), `t.ret()` returns
from a void function. The result names the function, the caller and the applied value.

```python
t.reach("HAL_ADC_Start_DMA")
t.ret("HAL_ERROR")
t.reach("Error_Handler")
t.check("no sequence published", t.read("app_state.adc_sequences"), 0)
```

Experiments: HAL — `HW_RCC_ERROR`, `HW_ADC_START_ERROR`, suppressing the publication from a void
callback (`HW_ADC_DMA_TIMEOUT`); CMSIS — `HW_CI_RET_VALUE`, `HW_CI_RET_RECEIVER`, `HW_CI_INJECT_ZERO`:
the receiver takes the forced 0 and enters its zero-result branch, which is visible after `t.finish()`.
**Environment:** a real frame of the called function, a verified prototype and ABI; a build without LTO.
`-Og -g3` does not guarantee that nothing is inlined.
**Boundary:** the function body is not checked, no physical fault is reproduced. For a void callback the
DMA has already completed — this is not a DMA timeout on the bus. After the injection, `reset_run` and
a positive run.
[ret](api/ret.md), [inject_zero](../../tests/firmware/common/tests/board/test_inject_zero.py),
[HAL runtime](../../tests/hal-f030/hal_scenarios/peripheral_runtime.py), [HAL fixture](F030_HAL_REGRESSION.md).

The [injection scenario](../../tests/firmware/common/tests/board/test_event_injection.py) compares two paths to a zero result: natural counter wrap and `ret("0")`. The latter skips producer side effects. Check both the receiver branch and producer state; the same result does not imply the same execution.

<a id="tech-005"></a>
## TECH-005 — Injecting an argument

**Goal:** take the real failure branch without damaging the configuration.

Stop at the right call by a condition, check the original argument, save the witnesses and write the
argument in the current frame:

```python
t.reach("rtc_wait", condition=f"error == {RTC_ERROR_LSI_TIMEOUT}")
t.check("LSI wait mask", t.read("mask"), t.evaluate("RCC_CSR_LSIRDY"))
t.write("mask", 0)
t.reach("board_rtc_fault")
```

Then check the error code, at least 1000 firmware ticks, an unchanged `RCC->BDCR` and no publications.
HAL: NULL into a configuration pointer (`t.write("RCC_OscInitStruct", "0")`) — only after reviewing the
guard in the source before the dereference ([TECH-009](#tech-009)).
**Environment:** the argument is available and writable in the frame, not removed by optimization;
SysTick runs, the external runner timeout is mandatory.
**Boundary:** the software deadline of one stage is checked, not a physical LSI failure and not the
accuracy of 1000 ms. After the injection, `reset_run` and a positive `HW_CI_RTC_ALARM`.
[rtc_deadline](../../tests/firmware/profiles/f030r8/tests/board/test_rtc.py), [protocol](F030_RTC_DEADLINE.md).

Temporarily change inputs through a context manager restoring them in `finally`. The [example](../../tests/firmware/common/tests/board/test_event_injection.py) restores only declared ticks/led fields, including exceptional exit. This does not roll back the PC, peripherals, time or the entire program state.

<a id="tech-006"></a>
## TECH-006 — Controlled peripheral state through MMIO

**Goal:** establish a specific peripheral state and check the application guard.

Select the exact SVD register, permitted width and reference-manual semantics. For an
ordinary RW register without side effects, explicit read → Python computation → write
may be appropriate. For command, W1C or FIFO registers use a separately justified value
and `allow_effects=True` when SVD requires it; generic RMW is unsafe there.
[MMIO contract](api/mmio.md): no hidden reads or write verification; ACK does not prove effect.

The technique was applied to ADC/DMA busy state, ADC disable and IRQ masking. Reusing the
word "busy" across F0 and F1/F4 does not transfer ADSTART or DMA EN semantics. Check initial
state, make one intervention, then independently check the guard and absence of publication.
Finish planned restoration with a normal acquisition repeat. Unknown restoration stops the series.

Older ADC scenarios use ordinary write; they are historical implementations, not examples
of the API 3 MMIO contract. For new code use [MMIO/SVD](MMIO.md),
[driver consistency](#tech-023) and [acceptance limits](API_ACCEPTANCE.md).

**Check the model before using it.** Establish which peripheral properties are modeled:
register access, side effects, protection, completion and errors. A limited Flash model used with
Renode 1.17 allowed LOCK bypass through CR and reported EOP without payload writes. These are
model limitations, not STM32 properties. Direct GDB MMIO access and CPU driver execution are
different paths; record which one was used. Check data and neighboring regions independently
of success flags; unknown or unsupported properties do not receive PASS.

<a id="tech-007"></a>
## TECH-007 — Independent numerical vectors and invalid inputs

**Goal:** check arithmetic through the real arguments and result of a firmware function.

Stop at the entry of the conversion function, write precomputed inputs, run to the publication and
compare the fields with a table. The expectations are analytic anchors, not copied from the code under
test; then invalid inputs (0, saturation, out of range) and the recovery of a normal result.

```python
t.reach("adc_convert_f103")
for name, value in zip(("temperature", "reference"), values):
    t.write(name, value)
t.reach("board_delay_ms")
t.check([(f"board_adc_reading.{field}", f"board_adc_reading.{field}", value)
         for field, value in zip(("vdda_mv", "temperature_mdeg_c", "quality"), expected)])
```

**Environment:** available arguments, sizes and signedness of the C types, MCU calibration data.
**Boundary:** arithmetic is checked, not sensor accuracy; mdegC does not promise 0.001 °C accuracy.
Do not move the F4 two-point calibration to F030.
[F030 vectors](F030_CMSIS_ADC_UNITS.md), [adc_vectors F030](../../tests/firmware/profiles/f030r8/tests/board/test_ci.py),
[adc F103](../../tests/firmware/profiles/f103c8/tests/board/test_adc.py).

<a id="tech-008"></a>
## TECH-008 — Interrupted WFI context

**Goal:** confirm the wake-up from Sleep by the chosen IRQ.

Isolate the source: save `NVIC->ISER`, mask the other IRQs and stop SysTick with a `t.write(rows)`
table, restore with one table in `finally`. In the handler, check the exception number, unwind to the
interrupted frame with `t.frames()` (a frame with `method == "signal"` is the exception trampoline and
is skipped) and read the halfword before the saved PC with `t.memory()`:

```python
chain = t.frames(FRAME_LIMIT)["frames"]
interrupted = next((frame for frame in chain[1:] if frame["method"] != "signal"), None)
instruction = int.from_bytes(t.memory(interrupted["pc"] - 2, 2), "little")
```

WFI in Thumb is `0xBF30`. An IRQ may arrive before WFI: the attempts are bounded and their contexts are
kept in the report. F103: RTC Alarm (IRQ41) is in the second NVIC bank; save and restore both banks.
Re-arm the RTC in thread mode, where SysTick runs.
**Boundary:** this is not a current or sleep-duration measurement and not a Stop/Standby check. IRQ
isolation changes the environment: restore in `finally`, then `reset_run`; a failed restore is not hidden.
[sleep F030](../../tests/firmware/profiles/f030r8/tests/board/test_sleep.py), [protocol](F030_CMSIS_SLEEP.md),
[F103](F103_CMSIS_RTC_SLEEP.md).

<a id="tech-009"></a>
## TECH-009 — HAL arguments and the verified source variant

**Goal:** choose the right HAL call by its arguments and check its inputs and effect.

A conditional stop chooses the call: `t.reach("HAL_GPIO_Init", condition="GPIOx == GPIOA")`. The
argument fields are checked with a table in its frame using HAL identifiers (`"GPIO_Init->Mode"`
against `"GPIO_MODE_OUTPUT_PP"`); the register is checked separately after the call. A NULL injection
is allowed only after reviewing the guard before the dereference. The HAL package name does not replace
the source hash: the mutable and the `const` RCC variants need different strict contracts; an unknown
hash is an error. [Scenarios and boundaries](F030_HAL_GPIO_RCC.md),
[hal_methods](../../tests/hal-f030/profile/tests/board/test_hal_methods.py).
A source review does not prove the behavior on hardware.

<a id="tech-010"></a>
## TECH-010 — Check tables

**Goal:** check several target values with one construct and a clear report.

`t.check(rows)` takes rows `(name, actual)` and `(name, actual, expected)`. A string cell is a GDB
expression, evaluated when its row is checked; a number, a `bool` and a matcher (`within`, `near`,
`one_of`, `matches`) are Python values. A two-cell row checks truth. The structure of all rows is
validated before the first evaluation, the first mismatch stops the table, and an evaluation error of
a cell names the row and recalls the rule.

```python
t.check([
    ("only channels 16/17", "ADC1->CHSELR", "ADC_CHSELR_CHSEL16 | ADC_CHSELR_CHSEL17"),
    ("forward scan", "ADC1->CFGR1 & ADC_CFGR1_SCANDIR", 0),
    ("plausible VDDA", "board_adc_reading.vdda_mv", PLAUSIBLE_VDDA_MV)
])
```

The GDB functions `$_streq`, `$_strlen`, `$_memeq`, `$_regex` work in string cells
([TECH-018](#tech-018)). The table for writes is `t.write(rows)`; a series of reads needs no table:
`dict(zip(paths, map(t.read, paths)))`.
**Boundaries:** a Python value computed while the list is built (`t.read(...)` in a cell) is read before
the first check; the rows are sequential reads, not an atomic snapshot. FIFO and read-to-clear need the
usual care. `reach`, writes and dependent calculations are not moved into a table. A Python string
(`result["outcome"]`, `profile.case["id"]`) does not belong in a cell — it would be evaluated as a GDB
expression; such checks stay separate.
[check](api/check.md), [matchers](api/matchers.md), host — `tests/host/test_target_extras.py`.

### Text and bit masks

```python
# Scalar strings are literal text; table strings are GDB expressions.
t.check("state text", "READY", "READY")
t.check([("enabled", "(flags & 0x20) != 0", 1)])
t.check("raw mask", t.read("flags & 0x20"), 0x20)
```

Mask `0x20` is not `1`. Normalize only for a boolean expectation; retain the mask when checking
bits. A pointer can be read as a numeric address, not the object at that address; dereference it
explicitly. Compare `sizeof` with `gdb.lookup_type("Packet").sizeof`; converting a nonzero size
to `bool` yields `True`, not a size.

### Evaluate once before writing

API 3 evaluates RHS once, but function calls in data expressions are forbidden.
If executing code is required to obtain a sample, invoke it explicitly and check the result:

```python
# next_sample is a placeholder no-argument function returning a number.
result = t.call("next_sample")
t.check("sample returned", result["return_state"], "available")
t.write("sample_copy", result["return_value"], verify=True)
```

This is ordinary def; async def requires await call. Call and write are not atomic.
LHS must be stable; MMIO requires its dedicated interface.

<a id="tech-011"></a>
## TECH-011 — Collecting measurements and calculating from records

**Goal:** collect a series of results published by the MCU and calculate statistics over the finished series.

1. The series parameters live in `api.toml [user.measurement]`; the scenario reads them through
   `t.profile.user["measurement"]` and checks them before navigating (`within(2, 20)`, `one_of(1, 2, 3)`).
2. In each iteration, run to the publication point, check freshness by the MCU counter with its width,
   read the values in a consistent state.
3. `t.record("measurement.sample", {...})` with the original units and the number. Check quality and
   plausibility; on a repeat, a gap or an error, do not produce a successful summary.
4. Get `t.records(...)` once, check completeness, calculate `mean`/`stdev` (ddof=1, N ≥ 2) and record a
   separate summary.

**Boundaries:** a record number does not mean a new MCU sample; halting the core does not freeze the
peripherals. Do not replace gaps with zeros and do not hide them by filtering. A small deviation does not
prove accuracy. Record limits are set in `api.toml`; a repeated `records()` makes additional copies.
[measurements](../../tests/firmware/common/tests/board/test_measurements.py),
[measurement_series](../../tests/firmware/common/tests/board/test_measurement_series.py),
[record](api/record.md), [records](api/records.md).

**Events and intervals.** The [example](../../tests/firmware/common/tests/board/test_event_intervals.py) records source, epoch, counter width and nominal rate with each sample. Modular subtraction requires matching metadata and an external guarantee that the interval is shorter than one period; it cannot detect missed complete wraps. `board_ticks_ms` denotes nominal firmware ticks, not calibrated time. A Python delay while halted does not measure MCU execution time.

### Required data and separate analysis

Records hold arbitrary supported data, not only measurements. The consumer defines names, fields,
units and expected sample counts. A `bool` is valid journal data but need not be a valid measurement:
use `type(value) in (int, float)` when excluding booleans. Convert `gdb.Value` and `bytes` explicitly,
for example with `int(value)` and `data.hex()`; the type does not establish units.

For file analysis, validate capture ownership/integrity first, then required completeness, record
presence/count, fields/types/units and finally numeric conditions. `all([])` returns `True`:
an empty selection must not pass a measurement check. A `record()` error and a missing capture
file are failures at different stages.

Keep the analysis verdict separate from the scenario outcome. Analysis may distinguish insufficient
evidence (ERROR) from complete out-of-range data (FAIL); that is consumer policy, not a new module
result schema. Analysis PASS never cancels scenario FAIL. An exact count of two or rejection of
interrupted series is not universal: define these policies before running the specific experiment.


<a id="tech-012"></a>
## TECH-012 — Expected refusal of an operation

**Goal:** check that an API operation refuses with the right code and details, and record it as a verdict.

```python
with t.refused("limit_exceeded", name="one point over the budget is refused"):
    t.breakpoint(spare)
with t.refused("command_failed", name="an unknown symbol fails") as failure:
    t.evaluate("api030_no_such_symbol")
t.check("failed expression keeps the cause", failure.error.__cause__ is not None)
```

A block without a refusal, another code or another detail is a failed check with the actual values.
`CheckFailed` and unrelated exceptions pass through unchanged. After the block, `failure.error` holds the
caught `ApiError` for further checks.
**Boundary:** `refused` checks an API refusal, not a firmware failure; a firmware failure is checked
through its state ([TECH-004](#tech-004)–[006](#tech-006)).
[refused](api/refused.md), [point_budget](../../tests/firmware/common/tests/board/test_point_budget.py),
[evaluate](../../tests/firmware/common/tests/board/test_evaluate.py).

<a id="tech-013"></a>
## TECH-013 — Who writes: a watch point and the frame chain

**Goal:** find the function that changes an object, and its callers.

```python
with t.watch("app_state.ticks"):
    stop = t.resume()["stop"]
    t.check("the stop is the watch point", stop["kind"], "watchpoint")
    names = [frame["name"] for frame in t.frames(4)["frames"]]
```

Frames describe the stop location, not necessarily the store instruction. Check the new value,
retain stop and frames with record(); external analysis requires explicit journal output.
Compare PC with symbol() and disassembly of the actual ELF. HW_CI_WHO_WRITES checks a known
firmware location, not a universal writer identification algorithm.
**Environment:** a hardware watch point and an addressable object of its declared size.
**Boundary:** the core may stop after the store; delay has also been observed on Cortex-M3,
not only M0. If a subsequent call executes, the writer may be in the calling frame.
Unwinding in an epilogue may be incomplete. Neither frames[0] nor frames[1] is automatically
the writer: source, instructions and a valid chain are required. Insufficient evidence leaves
the writer unidentified. Do not compute the store address as PC - 2: instruction lengths and
execution paths differ. The inferred flag classifies the stop reason, not the writer.
The API guarantees neither a fixed instruction delay nor a complete chain. DMA and other
bus-master writes are invisible to a core watch point.
On AT32/J-Link the function had returned after its final store and was absent from the frame chain.
[watch](api/watch.md), [frames](api/frames.md),
[who_writes](../../tests/firmware/common/tests/board/test_who_writes.py).

<a id="tech-014"></a>
## TECH-014 — Calling a function as a predicate

**Goal:** call a firmware function on the halted core as a check without leaving a trace in the state.

Take the bytes of the affected object with `t.memory(address, size)`, call `t.call(...)`, check the
result and the effect, restore the bytes with `t.memory(address, snapshot)` and compare them with the
original.

```python
state = t.symbol("app_state")
snapshot = t.memory(state["address"], state["size"])
result = t.call("app_step")  # placeholder no-argument function
t.memory(state["address"], snapshot)
```

**Boundary:** only the saved object is restored; peripherals, static variables of the function and other
side effects of the call remain the author's responsibility. `memory()` writes only into the profile SRAM.
[call](api/call.md), [memory](api/memory.md),
[call_predicate](../../tests/firmware/common/tests/board/test_call_predicate.py).

**A return value does not replace an effect.** Define the expected change and invariants before
the call. Afterwards compare the return value, exact data, operation counters and unchanged
neighboring regions. A driver counter establishes logical driver operations, not physical bus
transactions. Restore state even after an assertion fails; preserve restoration failures separately
from the original error. A byte copy is not universal C++ restoration: account for lifetime,
pointed-to memory and external resources. See [deferred writes](#tech-020) for a specific case.

<a id="tech-015"></a>
## TECH-015 — Choosing the right stop

**Goal:** stop at the right call without iterating over stops in the scenario.

`t.breakpoint(location, ignore_count=N)` passes N calls; `point.condition` changes the condition of a
live point; `point.disable()` keeps the point and its counter but frees its budget slot;
`t.reach(location, condition=...)` is a one-off conditional stop (`"error == 3"`, `"GPIOx == GPIOA"`).
The profile `breakpoint_limit` budget counts only active points, the fault handler points included;
a point over the budget is refused with `limit_exceeded`.
**Boundary:** GDB evaluates the condition at every hit, the core halts and continues — this changes the
timing of the firmware.
[breakpoint](api/breakpoint.md), [Point](api/point.md),
[conditional_stop](../../tests/firmware/common/tests/board/test_conditional_stop.py),
[point_budget](../../tests/firmware/common/tests/board/test_point_budget.py).

**Waiting for a change.** The [scenario helper](../../tests/firmware/common/tests/board/test_wait_changes.py) checks the stop kind and its own point ID before the predicate. Its `matched`, `exhausted`, `unexpected-stop` outcomes are an example convention, not new API outcomes. Do not hide a foreign stop by resuming again. A stop-count budget does not replace the scenario timeout. `with` removes its point on normal or exceptional exit; killing GDB requires external recovery. ID evidence may be native or inferred: retain it with the result.

<a id="tech-016"></a>
## TECH-016 — Stop location: a function, not a line number

**Goal:** stop at the right stage so that the scenario does not break with an edit of the source.

A stage of the code is named by a function: `reach` at its entry, `finish` after it returns (the result
names `returned_from`, the current function and the return value), `step`/`until(function)` inside it.
To see what a function did, leave it with `finish` and check the published state:

```python
t.ret("0")
t.check("the receiver returned to the loop", t.finish()["function"], "app_loop")
```

A `file:line` location breaks with any edit of the source, an added comment included. It is allowed
only where line locations themselves are checked (`HW_CI_UNTIL_TARGET`); a host test keeps it there.
[finish](api/finish.md), [until](api/until.md), [step](api/step.md),
[return_value](../../tests/firmware/common/tests/board/test_return_value.py),
[until_target](../../tests/firmware/common/tests/board/test_until_target.py).

<a id="tech-017"></a>
## TECH-017 — The run profile as an environment check

**Goal:** make sure the scenario runs on the declared chip, image and stand.

`t.profile` joins `target.toml`, the effective `api.toml`, the project data files, the build facts, the
case, the stand and GDB. The identity register and the flash size are read at addresses from the profile;
the vector table of the image through `t.memory(flash_start, 8)`; the `board.toml` data file through
`t.profile.data`; the build through `t.profile.build` (compiler, Cube packages, CMSIS/HAL, defines).
Profile values are Python values, so they are compared with separate checks and matchers, not with
table rows.
**Boundary:** the profile describes the declared environment; a flash size that differs from the profile
is a warning when the image fits both ([TARGET_IDENTITY](TARGET_IDENTITY.md)).

Initial SP in the vector table is a stack-top pointer, not a byte address to dereference.
For the selected contiguous RAM region `[start, end)`, a descending stack may start at `end`
(as `_estack` is defined in the checked ELF images). For an initial stack with 8-byte alignment
and room for the first saved value, use:

```python
# start/end describe the selected stack RAM region from the board/linker configuration.
initial_sp = int.from_bytes(t.memory(t.profile["flash_start"], 4), "little")
t.check("initial SP in stack region", start < initial_sp <= end)
t.check("initial SP aligned", initial_sp % 8, 0)
```

Reading a nonempty block requires different bounds: `start <= address` and `address + size <= end`.
Do not read at `end`. The project defines the size and selected bank; the broad SRAM window in
`memory()` does not establish physical accessibility of that entire region. An SP check proves
neither sufficient stack space nor separation from data/heap. Live SP after a prologue may differ
from the vector and must be checked separately. On six checked ELF images the vector equals
`_estack = end` and the final 8 bytes of selected RAM are readable; no out-of-region access is made.

[profile](api/profile.md), [profile scenario](../../tests/firmware/common/tests/board/test_profile.py).

<a id="tech-018"></a>
## TECH-018 — Firmware strings

**Goal:** check C strings of the firmware.

Two equal ways. In a table, GDB functions in a string cell:
`("version field equals", f'$_streq(app_info.version, "{VERSION}")')`, `$_strlen`, `$_memeq`, `$_regex`.
In Python, `t.evaluate(path, as_type=str)` reads a `char` array up to its zero or a `char *` pointer
(at most `STRING_LIMIT`) and is compared with a plain check or `matches(pattern)`. A string literal in
`$_memeq` needs memory allocated in the target; compare memory objects.
[evaluate](api/evaluate.md), [strings](../../tests/firmware/common/tests/board/test_strings.py).

<a id="tech-019"></a>
## TECH-019 — C++ context and typed reads

**Goal:** inspect an object, overload argument and naturally executed return.

```python
t.reach("Converter::apply(int) const")
frame = gdb.newest_frame()
obj = frame.read_var("this").cast(gdb.lookup_type("Converter").pointer())
t.check("object bias", int(obj.dereference()["bias"]), 7)
returned = t.finish()
```

Import `gdb` in the scenario; run its calls on the main GDB thread. A full signature distinguishes
overloads. API 3 reach accepts one outer pair of GDB single quotes
(`t.reach("'Converter::apply(float) const'")`); the previous release required the unquoted form. Snapshot values before changing frames. `is_optimized_out`
differs from a missing symbol and from actual zero; lazy fetching may fail. Store plain Python
data in records, not live gdb.Value objects. Check a return when available, and independently
check the published program result.

**Verified:** [standalone buildable example](../../tests/cpp-context/README.en.md), six boards,
Og/O2, `-g3`, soft-float, no LTO. Arguments were available in both builds; this does not establish
an optimized-out hardware case. RTTI, exceptions, inheritance and hard-float were not tested.
[Scenario](../../tests/cpp-context/profile/tests/board/test_cpp_context.py),
[read](api/read.md), [evaluate](api/evaluate.md), [finish](api/finish.md).

### Calling a live object's method in a sandbox

Stop after construction while the object, adapter and argument buffer are still alive. Select
the owning frame and retain typed pointers in GDB convenience variables. Do not reuse them after
their lifetime ends. Obtain sizes from debug information; an arbitrary "free" SRAM address is not
an allocated buffer. Check that callable method code exists in the ELF and whether the call can
wait for interrupts, delays or resources.

GDB Python example after selecting the frame containing `interactive` and `call_byte`:

```python
# The live object and argument storage belong to the neutral example.
gdb.execute("set $cache = &interactive")
gdb.execute("set $input = &call_byte")
assert int(gdb.parse_and_eval("$cache->write(5, $input, 1)")) == 1
assert int(gdb.parse_and_eval("$cache->dirty()")) == 1
```

This executes CPU code, rather than reading an object copy. Also check effects using
[TECH-020](#tech-020). Call the GDB API only from GDB's main thread.

**Scope of this experiment:** Windows, Renode 1.17, neutral Cortex-M4 ELF, C++17, `-O0`, no LTO,
GDB 14.2.90 with Python 3.11.4. Calls used `gdb.parse_and_eval`, not the regular `Target.call()`.
PC/SP matched before and after the series; GDB's warning about assuming MSP remained.
This does not verify all registers, PSP, ISR, RTOS, optimized builds or real hardware.
These limits concern forced sandbox calls, not the hardware example above.

The published neutral [C++/GDB/Renode example](../../tests/renode-cache/README.en.md) includes
commands, host checks and a separate scenario; it is not part of the hardware CI matrix.

### Call validation and complete restoration

`Target.call()` accepts a plain function name and numeric arguments; a free C++ function can fit
that interface. `Object::method` and `object.method` do not become valid names merely because an
[ELF contract](CONTRACTS.md) passed. Direct `gdb.parse_and_eval` is a separate path whose effects
and evidence the scenario must retain. An inline declaration does not guarantee a callable body.
Hidden `this` may have type `Object * const`, distinct from `Object *` and `const Object *`;
do not remove qualifiers just to pass preflight.
API 3 (0.5.0) accepts `Object * const` in an explicit this contract;
`tests/renode-startup/run_cpp.py` separates offline inspection from a real call in Renode.

Before changing ordinary memory, compare an independently known layout with DWARF, then check
the returned byte count against the size. Equality of two equally short snapshots proves nothing.
In a neutral example, guards before and after the object help: check them immediately after mutation
and after restoration. API 3 (0.5.0) validates response length in `memory()`, but the scenario still owns the requested object size.

After a body exception, restore in `finally`, then read back and compare the entire agreed region.
Retain body and restoration failures separately; unconfirmed restoration prohibits further changes.
Successful restoration does not cancel the original failure. `finally` cannot guarantee recovery
from process death or lost connectivity; byte copies cannot restore external resources or arbitrary
C++ invariants.

These boundaries were additionally checked on a neutral ELF with Windows/Renode 1.17, GDB 14.2.90,
`-O0 -g3`: types/calls and restoration of simple RAM. Transport failures were injected in a host model;
actual GDB short reads and DMA restoration were not established.


<a id="tech-020"></a>
## TECH-020 — Deferred writes and idempotence

**Goal:** distinguish cache changes from persistence and detect missing or redundant writes.

Prerequisites: a known initial image, owned objects and buffers, independent storage reads and
an observable logical-store counter. Define expectations independently of the implementation.

| Action | Check |
| --- | --- |
| Write a changed byte to the cache | Success, dirty set, storage and store counter unchanged |
| Commit a dirty cache | Exact image matches, dirty cleared, counter increases by one, neighbors unchanged |
| Commit a clean cache again | Success without data or counter changes |
| Supply an out-of-bounds range | Refusal without cache, storage or counter changes |
| Simulate failure or incorrect readback | Error detected, dirty retained, retry checked separately |

Use a host fake first for failures and partial changes. Then check GDB calls and the memory image
in an emulator. Establish a known starting state for each independent case; afterwards verify
restoration or terminate the emulator instance owned by the experiment. The contract defines
dirty behavior when a byte is changed back; it need not automatically become false.

**Verified:** 39 host checks of a neutral wrapper; two independent Renode cycles confirmed C++
calls and persistence effects. Failures and corrupt readback were checked with a host fake,
not a Renode fault model. Selected boundary-page erases were checked in the model; protection,
physical programming, endurance and power loss are not established. This is a scenario technique,
not a new storage API or hardware acceptance of EEPROM/Flash.



## Techniques from consumer practice

TECH-021–026 generalize mcu_power_board bridge, charging state machine, statistics and
telemetry scenarios. They are transfer recommendations with a neutral TECH-021 example, not
repeated hardware acceptance. Application thresholds, addresses, protocols and wiring
are not transferred. Every application needs its own oracle and admission conditions.

<a id="tech-021"></a>
## TECH-021 — Event ordering and the next operation

[Executable host/Renode example](../../tests/stateful-buffer/README.en.md): two defects,
fix, repeat and restoration; peripherals are not modeled.

**Goal:** detect residual state and handler interaction defects. Use owned objects and
buffers, known head/tail and completed initialization; save state as in [TECH-019](#tech-019).

| Intervention | Independent expectation |
| --- | --- |
| Partial packet, then completion or timeout | Only a complete valid packet is published; defined state after timeout |
| Next packet with different length and contents | Exact bytes and length, no previous tail; independent CRC |
| RX error while TX is busy | No cancellation, duplicate transmission or current TX modification if required by the contract |
| TX completion before/after queue inspection | No loss/duplication, tail advances by exactly the transmitted data |
| Ring buffer wraps | Next segment is transmitted in order, guards remain intact |

Check intermediate states and the next cycle without reset. Start independent cases from
equal preconditions; restore objects, buffers and resources after the series. An explicit
callback invocation checks the chosen ordering, not all races or actual IRQ/DMA delivery.
Restoring bytes does not undo data already sent over UART.

<a id="tech-022"></a>
## TECH-022 — Logical time of a state machine

**Goal:** quickly check debounce, backoff, retry and state duration limits. Define a
transition table first: state, input, duration, expected state and permitted action.
Check threshold −1, threshold and threshold +1, repeated input and counter wrap, accounting
for counter width and the maximum interval.

Change only a controlled time source and inputs, then execute one step. Use an isolated
state machine without physical outputs in a neutral example. Writing the system tick on
a board affects other tasks; an object snapshot is insufficient: require agreed isolation,
an inventory of affected clocks/arguments/outputs and restoration. Delays, IRQ waits and
held locks may make GDB invocation unsuitable.

**Limit:** virtual time establishes transition logic, not actual latency, scheduler behavior,
watchdog behavior or load safety. Check those with a live window and a separate timing witness.
Halting the CPU does not freeze all peripherals.

<a id="tech-023"></a>
## TECH-023 — Driver and peripheral consistency

**Goal:** check error recovery on both sides. Define valid combinations of driver state,
counters, flags and DMA state using the specific MCU/HAL documentation. For example,
READY with an active receive DMA may be inconsistent; this is not a universal driver rule.

Match Instance/channel and SVD to the target before access. Save RAM separately from registers;
use [MMIO](api/mmio.md) according to register access rights and effects. Before changing a
buffer/counter, disable the owned stream and confirm it stopped. After error injection check
consistent state, preservation of the other direction, restart and receipt of the next block.
Restore in reference-manual order, without copying a generic snapshot into W1C/FIFO registers.
A restoration failure terminates the series.

**Limit:** SVD and a server response do not establish physical effects. State injection does
not establish the hardware fault mechanism; Renode establishes only model behavior.

<a id="tech-024"></a>
## TECH-024 — Diagnostic cost and counter wrap

**Goal:** ensure diagnostics do not cause unacceptable load and counters survive wrap.
Record frequency, width, halt/sleep counting behavior and measured boundaries; DWT is not
available on every Cortex-M. Check measurement overhead with a separate control. Retain
all samples, the warm-up exclusion rule, median and maximum; define the limit beforehand.

For an n-bit counter use modulo 2**n subtraction only when the increment between
reads is strictly below 2**n, established from an upper bound on counter rate. Run across a wrap boundary and compare increments against an independent
time reference; missing samples make the conclusion unknown. Restore counter configuration
and debug enables if modified.

**Limit:** measured GDB-call duration is neither WCET nor free-running duration under IRQ/RTOS.
Host time includes transport; comparing two derivatives of the same MCU clock does not
establish its absolute frequency.

<a id="tech-025"></a>
## TECH-025 — Irregular samples and filter quality

**Goal:** separate calculation errors from noise, outliers and transient response. For an
event rate, supply equal intensity at different intervals, zero increments, counter wrap
and invalid dt. Compute expectations independently; for an agreed exponential filter,
for example, alpha = 1 − exp(−dt/tau), not a copy of MCU implementation code.

Use separate experiments for steady-state noise, input steps, isolated outliers and convergence.
Retain raw/filtered values, units, publication time and sample sequence. A new system tick
does not imply a new measurement. Check unique sample count before analysis; do not include
transients in stationary variance. Restore the input source and filter state.

**Limit:** lower variance does not prove accuracy. An independent input reference is required;
a physical source, allowed levels and restoration require separate agreement.

<a id="tech-026"></a>
## TECH-026 — Live window and external witness

**Goal:** relate internal state to another stand participant's observation. The mcu_gcs_board
radio simulator provides controlled input to mcu_power_board; the hwlivetest-android
engineering tool can record MCAP. These are stand roles, not automatically supported module
backends or importers.

Prepare capture and cleanup of all owned processes before resume; confirm receiver readiness.
Use a bounded [API 3 live window](LIVE_EXECUTION.md), without blocking the GDB thread waiting
synchronously for an external process. Stop the target after the window, finish and flush
capture, and verify restoration. Handle timeout and partial startup; finally alone does not
cover process death, and a remote process needs separate ownership.

Bind records to run ID, revision/ELF, source, units, message sequence and a time base with
known uncertainty. Detect gaps and duplicates. MCAP/rosbag are containers: define required
channels and fields beforehand; missing data are not zero. Preserve scenario, capture,
analysis and restoration outcomes separately ([TECH-011](#tech-011)).

**Limit:** reading the same value via GDB and telemetry checks delivery/consistency, not
independent sensor accuracy. Process PASS does not imply a valid capture.

## Extending the catalogue

On new experience, first look for an existing card; a new ID only for a distinct technique. Link HAL and
CMSIS variants without declaring them equivalent. Record the build and context preconditions, the action,
an independent criterion, the intervention, the recovery, the limits and a link to the code or protocol
with MCU, HAL, GCC, GDB and backend. Separate "verified", "candidate" and "not verified"; the first errors
are part of the experience too. Update RU and EN, scenario comments and the style test together. After a
HAL or optimization change, repeat the affected preflight and hardware runs, not only the links.

API 3 (0.5.0) removes repeated RHS evaluation: see the [write contract](api/write.md). Explicit pre-evaluation remains useful for older versions.

## Investigating peripheral accesses

Before applying techniques to MMIO, use the [API limitations](MMIO.md) and
[Renode skill resource](../../skills/stm32-gdbtest-renode/references/mmio.en.md).
Correlate three layers: method call → GDB/RSP request → model callback.
Define expectations from register semantics before running, independently of the model result.
Check positive and negative cases in Renode first, then repeat the minimal segment on your
target with the specific server and safe recovery. This is an investigation recommendation,
not a new scenario syntax rule or proof of exact physical transaction count.
WO/W1C/FIFO cannot be handled using a generic RAM snapshot.


Live windows in 0.5.0: ordinary scenarios remain supported; `async def`,
`resume(sync=False)`, `await wait()` and `await halt()` — [contract and migration](LIVE_EXECUTION.md).


API_VERSION=3 preserves synchronous navigation in ordinary def. In async def, await reach/step/until/finish/resume()/reset/call; resume(sync=False), ret and data methods remain immediate. Do not hide inferior calls in data expressions. See [LIVE_EXECUTION](LIVE_EXECUTION.md) for migration and limits.
