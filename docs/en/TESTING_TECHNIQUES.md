# Testing techniques catalogue

[Documentation](index.md) · [Русский](../ru/TESTING_TECHNIQUES.md)

## Production scenario style

- Module header: concise purpose in Russian and English; all other comments are English.
- A brief purpose comment precedes each function. Use two blank lines between functions and after imports.
- Separate meaningful blocks inside functions with one blank line; explain check groups and nontrivial loops.
- Keep lines of up to 120 characters intact. Split longer constructs at meaningful boundaries.
- Omit optional trailing commas in calls, lists, dictionaries and tables.
  A singleton tuple requires its comma: `labels=("adc",)`.

Applied to 35 production CMSIS/HAL scenario and minimal-consumer helper files.
Executable ASTs were compared with `ebf1bf8`: no differences (module docstrings excluded).
Historical research snapshots remain unchanged; the hardware campaign was not repeated.


Production first-package examples and five-MCU verification: [TECH-010/011](../research/api-extension/en/scenario-migration.md).

A practical companion to [test authoring](TEST_AUTHORING.md). HAL techniques
remain documented after examples migrate to CMSIS: firmware changes, but
experience with GDB, DWARF, callbacks and injections remains useful.
These are method cards, not new specification requirements, APIs or coverage metrics.

## Using this catalogue

`TECH-NNN` IDs are stable: never renumber or reuse them. Titles may change;
anchors remain. Mark obsolete cards and link replacements instead of deleting IDs.
Reference a technique next to a nontrivial scenario action:

```python
# TECH-005: docs/ru/TESTING_TECHNIQUES.md#tech-005 (EN: docs/en/TESTING_TECHNIQUES.md#tech-005).
# Force the wait predicate false; this does not simulate a failed oscillator.
target.set_value("mask", 0)
```

Paths are relative to the module root. External consumers use a GitHub URL
pinned to their gitlink and the same anchor. `@case` and requirements retain
their IDs; TECH replaces neither ELF contracts nor traceability. No new decorator
or API field is introduced.

| Group | Techniques |
| --- | --- |
| ELF, build and observation | [001 macros](#tech-001), [002 context](#tech-002) |
| Asynchronous execution | [003 callbacks/IRQs](#tech-003) |
| Controlled failures | [004 function return](#tech-004), [005 argument](#tech-005), [006 MMIO](#tech-006) |
| Numerical checks | [007 vectors](#tech-007) |
| Sleep and interrupts | [008 WFI context](#tech-008) |
| Check organization | [010 tables](#tech-010) |
| Measurement series | [011 acquisition and calculation](#tech-011) |

The cards derive from executed examples. Another MCU, HAL, GCC or backend needs
fresh validation. Linked code/protocols do not promise identical results in every environment.

<a id="tech-001"></a>
## TECH-001 — ELF macros and independent expectations

**Purpose:** inspect configuration using HAL predicates/getters and CMSIS fields.
**Environment:** `-g3` in the relevant translation unit, correct MCU defines/HAL
and a macro context in the contract. `-g3` does not retain unused functions;
a definition in an installed header does not prove its presence in the ELF.

Prepare/contracts first, then reach the required context and use separate checks.
Compare mask results with masks or normalize them; do not always expect 1.
Define expected frequencies, divisors and physical channels independently:
F411 HAL TEMPSENSOR includes a service flag, while the hardware channel is 18.
Do not invent missing definitions through macro define to obtain PASS.

**Caution:** a getter can read FIFO/read-to-clear registers or participate in an
SR/DR sequence. Setters are separate injections. Clock enabled does not prove a
particular ENABLE macro executed. Pure observation needs no restoration; if a
read has side effects, define recovery and scope beforehand.
[HAL guidance and validated scope](HAL_MACRO_GUIDE.md).

<a id="tech-002"></a>
## TECH-002 — Capture an address before changing DWARF context

**Purpose:** compare one MMIO register before and after reaching another function.
Capture `&RCC->BDCR` where RCC is visible, then read through that address using
the correct type/width. Do not replace lost macro context with an arbitrary constant.

**Environment:** verified macro context and type width; this example targets a
32-bit STM32, not a universal MMIO helper. The address belongs to the same session
and memory map; do not reuse it across ELF files or targets.
**Limit:** this addresses lost macro context, not register read safety. The
technique itself performs no injection.
[RTC deadline: original ERROR and fix](F030_RTC_DEADLINE.md),
[rtc_deadline](../../tests/firmware/profiles/f030r8/tests/board/test_rtc.py).

<a id="tech-003"></a>
## TECH-003 — Callback/IRQ to published result

**Purpose:** connect a natural event to the correct peripheral instance and an
application state change. HAL: reach the callback, check its handle, then wait
for a second event and publication. CMSIS: check exception/flag, counter,
thread-mode return and published result.

**Environment:** visible symbols/arguments, operating IRQ/DMA and a suitable
freeze policy. The HAL weak callback must resolve to the implementation under test.
**Limit:** peripherals may keep running during halt. Callback frequency under a
debugger does not measure real throughput; software IRQ does not prove a physical
edge. Start the next scenario from the agreed reset state.
[Original HAL ADC/TIM/RTC cases](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/0c8c966f0429710e6e20472fbd9fe8898da7cfee/tests/scenarios/peripheral_runtime.py),
[CMSIS RTC](F030_CMSIS_RTC.md).

RTC requires family-specific expectations: F103 uses a counter/alarm rearmed in
thread mode, while F411 uses masked calendar Alarm A with natural periodic IRQs.
Do not copy the F03040 kHz prescaler to F41132 kHz.
[F411 RTC/Sleep and limits](F411_CMSIS_RTC_SLEEP.md).

<a id="tech-004"></a>
For Cortex-M exception numbers, use `SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk`. GDB names `xPSR`/`xpsr` depend on the server. Preflight the CMSIS macros in the required context. Reading VECTACTIVE does not clear flags or prove the physical IRQ source.

## TECH-004 — Override HAL return and suppress a callback

**Purpose:** test the caller's response while skipping a function body.
Two distinct experiments: `HAL_ADC_Start_DMA` → `force_return("(HAL_StatusTypeDef)1")`
checks Error_Handler; `force_return("")` from a void callback after DMA completion
suppresses publication and checks the deadline. Neither publishes a new sequence.

**Environment:** a real called frame, verified prototype/enum/ABI, arguments and
symbols. For call-path stepping and force_return use a build without LTO and
verify actual compile/link flags. `-Og -g3` does not guarantee absence of inline
or optimized-out entities. Prepare cannot replace runtime frame/backend checks.

**Limit:** the skipped HAL body is untested; no physical fault was reproduced.
DMA has already finished in the void callback case; this is not a bus DMA timeout.
After injection use reset_run and a separate positive ADC run; stop the series
if recovery fails. [Both original experiments](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/blob/0c8c966f0429710e6e20472fbd9fe8898da7cfee/tests/scenarios/peripheral_runtime.py).
The module fixture is still [planned](F030_HAL_REGRESSION.md); old PASS is not new PASS.

<a id="tech-005"></a>
## TECH-005 — Inject a wait-predicate argument

**Purpose:** exercise a real deadline branch without damaging oscillator setup.
Reach `rtc_wait` with `error == 3`, check the original mask, capture ticks and
BDCR, set mask=0 and reach rtc_fault. Check error3, at least 1000 firmware ticks,
unchanged BDCR and no application start/RTC publication.

**Environment:** a writable argument in the current frame; optimization has not
removed the function/parameter. SysTick must run; an external runner timeout is mandatory.
**Limit:** one stage's software deadline, not physical LSI failure or accurate 1000 ms.
Restore with reset_run, then positive RTC_ALARM.
[Code](../../tests/firmware/profiles/f030r8/tests/board/test_rtc.py), [protocol](F030_RTC_DEADLINE.md).

<a id="tech-006"></a>
## TECH-006 — Controlled peripheral state through MMIO

**Purpose:** exercise an ADC busy guard or missing IRQ publication. ADC_BUSY
checks idle, enables continuous conversion, confirms ADSTART, then checks error6
and absent data. This differs from TECH-004. ADC_TIMEOUT disables DMA IRQ, not DMA.

**Environment:** the actual MCU reference manual, RW/W1C/rc_w0 semantics and ADC
behavior during halt. Never generalize read-modify-write to arbitrary status
registers; report freeze policy and side effects. DMA/ADC may continue and cause OVR.
**Limit:** one constructed state, not all ADC/DMA faults. Restore with reset_run,
then normal ADC_DMA; recovery failure stops the series.
[ADC_BUSY](F030_ADC_BUSY.md), [code](../../tests/firmware/profiles/f030r8/tests/board/test_adc_faults.py),
[DMA timeout](F030_CMSIS_ADC_DMA.md).

F103: [ADC/DMA](F103_CMSIS_ADC_DMA.md) distinguishes the DMA EN guard, ADC
disable and missing IRQ notification. Reusing the name "busy" does not transfer
F0 ADSTART semantics to F1; record the state actually established by injection.

F411 uses DMA2 Stream0 (IRQ56 in NVIC bank1); normal mode stops the stream
in hardware. TIMEOUT masks the IRQ, not ADC requests; BUSY EN proves stream
ownership only. [F411 evidence](F411_CMSIS_ADC_DMA.md).

<a id="tech-007"></a>
## TECH-007 — Independent numerical vectors and invalid inputs

**Purpose:** test arithmetic through actual firmware function arguments/results.
Supply independently calculated inputs/expectations, check boundaries and invalid
inputs, then recovery of a normal result.
**Environment:** visible arguments, C type widths/signedness, integer truncation
and MCU calibration data. Do not copy expectations from the implementation under test.

**Limit:** arithmetic, not analog sensor accuracy. m°C does not promise 0.001°C
accuracy. Do not transplant two-point F4 calibration to F030. After argument
injection return to the normal loop/reset and check quality.
[F030 vectors and limits](F030_CMSIS_ADC_UNITS.md),
[adc_vectors/adc_invalid](../../tests/firmware/profiles/f030r8/tests/board/test_ci.py).

<a id="tech-008"></a>
## TECH-008 — Interrupted WFI context

**Purpose:** confirm progress after Sleep through a selected IRQ. Reach the
handler, check the exception, unwind the interrupted frame and inspect the
instruction before the saved PC. In this Cortex-M experiment WFI is halfword 0xBF30.
An IRQ can arrive before WFI: attempts are bounded and their contexts recorded.

**Environment:** GDB exception-frame unwinding, possibly through a trampoline;
required symbols/instructions exist. ISA/PC rules depend on architecture.
**Limit:** no current measurement, sleep duration or Stop/Standby evidence.
IRQ isolation changes the environment: restore enable bits in finally and finish
with reset_run; do not hide restoration errors.
[Code](../../tests/firmware/profiles/f030r8/tests/board/test_sleep.py), [protocol](F030_CMSIS_SLEEP.md).

F103: RTC Alarm IRQ41 uses NVIC bank1; SysTick/TIM2 isolation must save
and restore both banks, not only ISER[0]. Keep bounded RTC rearm waits in
thread mode where SysTick can run, not in an ISR that blocks lower-priority
SysTick. [F103 evidence](F103_CMSIS_RTC_SLEEP.md).

## Growing the guide

Look for an existing card before adding one. New IDs identify distinct techniques;
link HAL/CMSIS variants without declaring them equivalent. Record build/context
preconditions, action, independent criterion, intervention, restoration, limits
and code/protocol with MCU/HAL/GCC/GDB/backend. Distinguish validated, candidate
and untested uses. Update RU/EN and comments together. Initial errors are evidence too.
After HAL/optimization changes repeat affected preflight and HW checks, not just links.
Future topics: watchpoints, temporary freeze policies, sparse/full images and external
stimuli. Add cards as experiments are generalized, without promising new APIs.

<a id="tech-009"></a>

## TECH-009 — HAL arguments and reviewed source variants

Conditional reach selects the intended HAL call using GPIOx/Pin/ODR. Read argument
fields in their DWARF frame, then check the register separately after the call.
NULL injection here requires reviewing the guard before dereferencing.
A HAL package name is not a hash: mutable/const RCC variants require different
strict contracts. An unknown hash is an error, not a reason to drop type checks.
[Working cases and limits](F030_HAL_GPIO_RCC.md); source review is not HW evidence.


<a id="tech-010"></a>

## TECH-010 — Sequential table-driven checks

**Purpose:** remove repeated check/value plumbing from adjacent register assertions.
**Prerequisites:** one stopped context, available symbols/macros and expectations
independent of the setting being checked. Works with current rc.2; this is a consumer
helper, not a new API operation.

```python
def check_values(target, checks):
    for name, expression, expected in checks:
        actual = target.value(expression)
        if isinstance(expected, str):
            expected = target.value(expected)
        target.check(name, actual, expected)

# After reach and context preparation:
check_values(target, [
    ('RTC prescalers', 'RTC->PRER', (127 << 16) | 249),
    ('RTC vector', '(unsigned int)vectors[57] & ~1U',
     '(unsigned int)RTC_Alarm_IRQHandler & ~1U'),
])
```

These numbers/symbols target the corresponding F4 configuration, not every MCU.
String expectations are GDB expressions; numeric expectations are ready values.
Order remains actual → expected → check, stopping on the first exception with each
check's own label. An empty table checks nothing; authors ensure nonempty dynamic inputs.

**Boundaries:** keep reach/writes/dependent calculations outside tables; never place
value calls in table entries. Reads are sequential, not an atomic snapshot; FIFO/
read-to-clear and running peripherals during halt retain their original constraints.
No resume or write is added, nor automatic restoration. Preserve case/contracts and
context requirements. Single checks need no helper; for one structure's fields also
consider the existing fields operation.

**Verified:** 82 paired host cases for RTC F030, ADC F411 and TIM2 F103; 47 candidate
blocks including board variants. Hardware pairs confirmed on F030/F103/F411;
see the update below.
[Report, variants and boundaries](../research/api-extension/en/table-checks.md).

<a id="tech-011"></a>

## TECH-011 — Accumulate measurements and calculate from records

**Purpose:** stop after MCU publication, read ordinary values, record them and
calculate statistics after completing the series.
**Availability:** record/records and config are integrated into development Target
0.2.0.dev0. The historical facade remains for comparison. This is a consumer
technique, not another core operation.

1. Set count/expected quality/units in scenario parameters. Place consumer api.toml
   settings in [user.measurement] and validate them in the scenario.
2. Reach publication on each iteration; verify freshness with the MCU counter and
   its width. Read quality, VDDA and temperature in a consistent published state.
3. Record original units and acquisition sequence; check quality/range. Do not
   emit a successful summary after duplicate/missing/invalid samples.
4. Read records once, verify completeness, calculate mean/stdev and record a separate
   summary with count, units and ddof. Sample standard deviation requires N≥2.

**Boundaries:** journal sequence does not identify a fresh MCU sample; CPU halt does
not freeze every peripheral. Publication, DMA, read-to-clear and debugger timing
are application concerns. Never replace missing data with zeros or hide it by filtering.
Small deviation does not prove accuracy. Budget for N entries plus summary; repeated
records calls allocate additional copies.

Python calculations use captured data. For GDB arithmetic, transfer numbers with
 gdb.Value/convenience variables and use a fixed expression; run on the main GDB
thread and restore scratch variables. set_value, firmware calls and continuation are
separate actions with separate restoration requirements.

**Verified:** paired VDDA/temperature variant (5 outcomes), known mean/deviation
anchors, GDB14/GDB16 with 4 arithmetic sets each without MCU. Historical E1 hardware
results do not replace acceptance of the new variant.
[Python/GDB examples, paired scenario and evidence](../research/api-extension/en/measurement-technique.md).

[Update 2026-10-03: TECH-010/011 verified on three boards](../research/api-extension/en/techniques-three-boards.md): F030, F103, F411; 7/7 HW each with restoration. Earlier host-only boundaries still apply to negative cases; core unchanged.

[Acceptance after core integration](../research/api-extension/en/core-integration.md): three stands repeated, TECH-011 uses actual Target; 7/7 HW each, restoration PASS.
