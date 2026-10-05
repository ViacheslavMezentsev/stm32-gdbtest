# Testing techniques catalogue

[Documentation](index.md) · [Русский](../ru/TESTING_TECHNIQUES.md)

A practical companion to [test authoring](TEST_AUTHORING.md) and the [API reference](api/index.md).
The cards describe techniques verified by the bundled scenarios of the module: the shared ones
(`tests/firmware/common/tests`), the scenarios of the five CMSIS profiles (`tests/firmware/profiles`)
and the F030 HAL fixture (`tests/hal-f030`). These are method cards, not new specification
requirements, API operations or coverage metrics.

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
- A register read-modify-write is an expression as the value, `t.write(path, "REG | BIT")`; several
  writes in a row form a `t.write(rows)` table ([TECH-006](#tech-006)). A series of reads uses the
  built-in `map()`.
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

<a id="tech-006"></a>
## TECH-006 — Controlled peripheral state through MMIO

**Goal:** create a particular peripheral state and check the application guard.

A read-modify-write is an expression as the value; several writes in a row form a `t.write(rows)`
table. The expression is evaluated before the write, assignments are refused, the rows run in order
and their structure is validated before the first write:

```python
# Start continuous conversions while the core is halted: ADSTART stays asserted.
t.write([
    ("ADC1->CFGR1", "ADC1->CFGR1 | ADC_CFGR1_CONT"),
    ("ADC1->CR", "ADC1->CR | ADC_CR_ADSTART")
])
```

Experiments: F030 `HW_CI_ADC_BUSY` — an active conversion (ADSTART) before the application starts;
F103/F4 — the busy DMA guard (`DMA_CCR_EN`/`DMA_SxCR_EN`), a disabled ADC
(`t.write("ADC1->CR2", "ADC1->CR2 & ~ADC_CR2_ADON")`), a timeout by masking the DMA IRQ in the NVIC
rather than stopping the DMA. Carrying the name "busy" over does not carry the F0 ADSTART meaning to F1.
**Environment:** the RM of the particular MCU, RW/W1C/rc_w0 semantics, ADC/DMA behavior while the core
is halted. Peripheral registers are written without a read-back confirmation (`verify_scope=outside`).
**Boundary:** one state is created, not the whole set of ADC/DMA failures. Recovery is `reset_run`,
then a normal `HW_CI_ADC_DMA`; a failed recovery stops the series.
[ADC_BUSY](F030_ADC_BUSY.md), [adc_faults F030](../../tests/firmware/profiles/f030r8/tests/board/test_adc_faults.py),
[ADC/DMA F103](F103_CMSIS_ADC_DMA.md), [ADC/DMA F411](F411_CMSIS_ADC_DMA.md), [write](api/write.md).

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

Check the writer (`names[0]`), the caller (`names[1]`), the stop address inside the writer by
`t.symbol()` and the new value. Record the chain with `t.record()`.
**Environment:** a DWT hardware watch point; the object is addressable and of its declared size.
**Boundary:** on Cortex-M0 a watch point halts the core one or two instructions after the store. When
the store is the last instruction of the body, the stop lands in the epilogue, which carries no GCC
unwind information, and GDB loses the calling frame. In the fixture firmware body instructions follow
the store (`app_received.publications++`). Writes by DMA and other bus masters are invisible to a core
watch point.
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
result = t.call("app_step", "&app_state", "APP_MODE_BLINK")
t.memory(state["address"], snapshot)
```

**Boundary:** only the saved object is restored; peripherals, static variables of the function and other
side effects of the call remain the author's responsibility. `memory()` writes only into the profile SRAM.
[call](api/call.md), [memory](api/memory.md),
[call_predicate](../../tests/firmware/common/tests/board/test_call_predicate.py).

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

## Extending the catalogue

On new experience, first look for an existing card; a new ID only for a distinct technique. Link HAL and
CMSIS variants without declaring them equivalent. Record the build and context preconditions, the action,
an independent criterion, the intervention, the recovery, the limits and a link to the code or protocol
with MCU, HAL, GCC, GDB and backend. Separate "verified", "candidate" and "not verified"; the first errors
are part of the experience too. Update RU and EN, scenario comments and the style test together. After a
HAL or optimization change, repeat the affected preflight and hardware runs, not only the links.
