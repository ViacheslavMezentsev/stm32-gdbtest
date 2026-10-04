# CI scenario requirements (f411ce)

## HW_CI_BOOT
At main, initialized delay is 500 ms and BSS counters are zero. After board initialization,
consecutive app_loop entries advance app_state.ticks by one.

## HW_CI_GPIO
At the first board_led_toggle, GPIOC clock is enabled; PC13 is a low-speed push-pull output,
initially High (LED off on WeAct BlackPill). This checks registers, not emitted light.

## HW_CI_CLOCK
HSI supplies nominal 16 MHz with AHB/APB1/APB2 divide-by-one. SystemCoreClock agrees;
SysTick uses core clock with LOAD=15999, enabled with IRQ. No frequency accuracy claim.

## HW_CI_BLINK
PC13 alternates across consecutive board_led_toggle entries, separated by at least
500 firmware milliseconds. Debugger stops are excluded from physical timing claims.

## HW_CI_TIM2_INIT
TIM2 uses internal 16 MHz clock, PSC=15999, ARR=99 (nominal 100 ms), upcounting, UIE/CEN.
NVIC IRQ28 is enabled and vector slot44 points to TIM2_IRQHandler.

## HW_CI_TIM2_IRQ
Natural TIM2 update enters exception44 with UIF set. Each handler publishes one event;
thread mode resumes. No EGR/software-pending injection is used; no jitter claim.

## HW_CI_SYSTICK_IRQ
Natural SysTick enters exception15 through vector15. The handler increments the
millisecond counter once, then thread mode can resume. No external time reference.

## HW_CI_ADC_INIT
ADC1 PCLK2/2=8 MHz, scan CH18/17 at480 cycles, TSVREFE without VBAT. DMA2 stream0/channel0 normal halfwords, IRQ56/vector72.

## HW_CI_ADC_DMA
Two natural scans complete two transfers each, exception72/TC without errors; raw values publish before sequence, stream stops and flags clear.

## HW_CI_ADC_UNITS
Factory provenance=2 using F411 3.3 V/30/110 C samples; plausible VDDA and temperature, not metrology.

## HW_CI_ADC_VECTORS
Five analytic anchors exercise two calibration points, midpoint, negative temperature and VDDA compensation.

## HW_CI_ADC_INVALID
Nineteen invalid inputs: zero/saturation/uint16 maximum in five arguments, equal/reversed calibration, invalid supply. Zero reading then normal recovery.

## HW_CI_ADC_TIMEOUT
Mask IRQ56: DMA completes without publication; error4 after at least20 firmware ticks.

## HW_CI_ADC_BUSY
Enable stream before sample: DMA ownership guard error6, no publication; no claim of active ADC conversion.

## HW_CI_ADC_DISABLED
Clear ADON before sample: error3, no publication. Not a forced HAL return code.

## HW_CI_RTC_INIT
LSI, calendar RTC PRER127/249, masked Alarm A, EXTI17 rising, IRQ41/vector57; no backup-domain reset.

## HW_CI_RTC_ALARM
Two natural alarms enter exception57 with ALRAF/EXTI17 pending; one publication per handler, thread resumes.

## HW_CI_RTC_DEADLINE
Inject zero mask in LSIRDY wait: error3 after at least1000 ticks, backup configuration retained, no application/event publication. Not a physical oscillator fault.

## HW_CI_SLEEP_SYSTICK
With both external NVIC banks masked, exception15 interrupts WFI; delay completes and ADC sequence retained. Restore IRQ controls.

## HW_CI_SLEEP_TIM2
Only IRQ28 enabled, SysTick stopped: exception44 interrupts WFI without tick advance; restore controls and resume. Not Stop or a power measurement.

## HW_CI_ADC_SERIES
Capture configured 2..20 contiguous published ADC samples; validate quality and ranges,
then retain raw measurements and mean/sample standard deviation (ddof=1) using runtime records.
A missing, stale or invalid sample prevents a successful summary. Not sensor calibration.

## HW_CI_RET_RECEIVER
The firmware calls app_step through app_receiver_step, so a forced return reaches a caller that
consumes it: app_received.produced holds the forced 42 and then the forced 0, while the caller's own
app_state copy (ticks 7 and 9) never appears. The call counter advances per accepted value. A refused
out-of-range value is not covered here; value encoding is checked by the V14 prototype. The scenario
depends on the caller storing the value, not on the debugger alone.

## HW_CI_MEASUREMENT_SERIES
Five publications are taken with execution continuing between samples, so the series varies in time:
board_adc_sequences increases without gaps and the values stay inside the plausible -40000..125000
mdegC domain with more than one distinct value. Records keep every sample. This checks the measurement
protocol on varying data, not sensor calibration, sample rate or accuracy.

## HW_CI_READ_WRITE
Reading `app_state` returns a mapping with the declared fields `led` and `ticks` as plain integers,
identical to a single-member read and to a field-set read. Writing 41 into the `uint32_t`
`app_state.ticks` reports the previous value, the applied value and a verified read-back, records the
mutation in the report, and the application continues from the written value (42 on the next loop
iteration). The scenario verifies typed reads of scalars and structs and one verified write; it does
not measure memory access speed, float formatting or writes to peripherals.

## HW_CI_NAVIGATION
`finish()` completes the producer function and the caller's copy advances by one tick. A hardware point
set with `breakpoint()` is active, resolves at least one address and counts the observed stop; `resume()`
stops at that point, reporting `kind=breakpoint` and the function where it stopped, and leaving the
`with` block removes the point. Two instruction steps report `outcome=completed`, `completed=2` and a
step stop; `until()` completes the current line without a point stop. `reach()` returns its outcome,
the point number, the resolved addresses and the reached frame. The scenario verifies the navigation
surface; it does not claim source-line accuracy of a step or breakpoint counts of foreign points.

## HW_CI_RET_VALUE
`ret(42)` reports the operation, the producer, the caller, the supplied and applied values and the
encoded command `return (uint32_t)0x2a`, and records the mutation. The receiver consumes the forced
value, so the published `app_state.ticks` becomes 42 instead of the producer's own result. A value
outside the declared 32-bit width is refused with `out_of_range` before any command is executed and
leaves no mutation; a bare `ret()` issues the plain `return` without a value; `force_return` keeps the
0.2.x expression form. The scenario does not cover pointer or floating-point return types.

## HW_CI_CALL
`call("app_step", "&app_state", 1)` runs the real firmware function on the halted core: it reports the
operation, the function, the arguments, the built expression and an available return value equal to the
incremented tick count, and the application state itself changes. The mutation is recorded. A void
function runs without arguments and reports `return_state=void`. An unsupported argument value is
refused with `unsupported_argument` and an invalid function name with `invalid_function`, both before
the call and without recording a mutation. The scenario does not cover pointer, floating-point or
variadic parameter lists.

## HW_CI_EXECUTE
`execute("info registers pc sp")` returns the debugger text and journals the command, the stage, the
result, the output length, the truncation flag and the configured limit. An embedded newline stays in
the text instead of splitting commands. An output above the limit is reported as truncated and the
journal carries the SHA-256 of the full text. An empty command, a blank command and a command with a
newline are refused with `invalid_command` before the debugger is touched and leave no journal entry;
an unknown command is reported as `command_failed` with its cause. The scenario does not cover
non-ASCII output framing or commands that change debugger state.

## HW_CI_RESET
`reset()` with an active point is refused with `active_points` and `effect=none` before the command
runs, and the point stays active. After the point is removed the configured command `monitor reset halt`
halts the core, both invalidation steps report `done`, the reset is journalled and the halted pc is
reported. A fresh `reach("app_loop")` after the reset proves the invalidated caches are usable and the
application starts from the beginning. The scenario does not cover a failing backend command, which is
exercised by the host checks and by the earlier command-failure experiment.

## HW_CI_SETTINGS
`settings` is the effective run configuration and is the same frozen object as the 0.2.x `config`; it
exposes the api schema, the records limits, the execute output limit and the reset command, and both it
and its nested mappings refuse assignment with `TypeError`. `sources` is the same frozen object as
`config_props`: it names the `api.toml` reference, carries its SHA-256 digest and the captured data, and
refuses assignment. The scenario checks the read-only contract; it does not cover configuration
loading or schema validation, which the host checks exercise.

## HW_CI_EVALUATE
`evaluate("1 + 1")` returns 2 and keeps the declared integer type. `as_type` applies the requested
conversion: `float` gives 5.0 for `2 + 3`, `bool` gives true for a nonzero value and false for zero, and
`int` truncates towards zero for `(float)7 / 2`. A type name such as `"float"` is accepted as well. An
unknown symbol is reported as `command_failed` with its cause, an empty expression as
`invalid_expression`, and an unsupported `as_type` as `unsupported_type`. The scenario covers scalar
conversions; it does not cover structures, arrays or strings.

## HW_CI_REGISTERS
`registers("pc", "sp")` returns both values as integers: the program counter points inside Flash and
carries no Thumb bit, because GDB reports the instruction address, and the stack pointer lies inside the Cortex-M SRAM window
and is double-word aligned; the profile carries the flash region, so the SRAM window is checked as a range. `registers("r0", "r1",
"r2", "r3")` returns every requested general-purpose register inside 32 bits. An unknown register name is
reported as `read_failed` with its cause, and an empty request as `invalid_names`. The scenario reads
registers of the innermost frame; it does not walk older frames.

## HW_CI_FRAMES
`frames()` returns the chain from the innermost frame outwards: the first entry is the function the core
stopped in, its depth is zero, its method is `normal` and its program counter is an integer. The caller
`main` is on the chain and depths grow outwards without gaps. `frames(limit=1)` returns only the
innermost frame and reports `complete=false`, while a wide limit completes the walk. An unusable limit is
refused with `invalid_limit` before the chain is walked. The scenario checks the innermost and its
caller; it does not verify the whole boot chain.

## HW_CI_WATCH
`watch("app_state.ticks")` returns a point and `resume()` stops the running firmware on the next write:
the stop is classified as `watchpoint` because the reported point is a watch point, while the
watched object really changed. The native reason stays a hint: OpenOCD names `watchpoint-trigger`,
J-Link reports no reason at all. The point is removed when the context manager exits, so no watch point stays active
(the stand keeps its own fault guard).
A whole eight byte structure (`app_state`) is a valid target exactly like its field. An unknown path
and a non-object expression are refused with `invalid_path` at the validation stage, before the debugger
is touched and without leaving a point behind. The scenario verifies a write
watch point on a naturally aligned object; read watch points, larger objects and backends without
hardware watch points are not covered.
