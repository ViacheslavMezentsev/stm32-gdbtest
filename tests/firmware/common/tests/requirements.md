# CI scenario requirements shared by every profile

These scenarios run unchanged on every CI profile; profile directories hold only what differs.

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
Five publications are taken with execution continuing between samples: board_adc_sequences increases
without gaps and repeats, every value is real data and stays inside the plausible -40000..125000 mdegC
domain. The die temperature may keep one value for the whole series, so equal samples are accepted.
Records keep every sample. This checks the measurement protocol, not sensor calibration, sample rate or
accuracy.

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

## HW_CI_PROFILE
The scenario checks the environment it runs in through the read-only `profile`. The identity register
masked by `target.toml` equals the declared value and the flash size register covers the declared
`flash_size`; the vector table read with `memory` puts the initial stack pointer into SRAM and the Thumb
reset vector into the profile flash. The case section names this scenario, its function, timeout and
contracts; the stand section names a supported backend (`openocd` or `jlink`), a local or remote server
and an unset or positive speed. The captured `target.toml` carries a SHA-256 digest and is the origin of
`mcu`; the records limit and the reset command are readable by dotted path. The data file `board.toml`
declared in `session.toml [data]` gives a board name and an LED pin and is the origin of that value. The
build section names GCC, declares CMSIS headers and shows a CMSIS-only build without `USE_HAL_DRIVER`. The
GDB version is known before the first stop and the stop details capability after it. The whole profile is
recorded, and the sections refuse assignment. Configuration loading and schema validation are covered by
the host checks.

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

## HW_CI_TEST_ALIAS
A scenario declared with `@test(...)` runs exactly like one declared with `@case(...)`: the harness
collects it by that name, the identifier, labels, contracts and timeout are read from the decorator, and
the function receives the usual `Target`. The alias returns the decorated function unchanged. The
scenario proves that both names are interchangeable; it does not check the metadata of other scenarios.

## HW_CI_INJECT_ZERO
At the entry of `app_step` a forced return of 0 skips the producer body. After `finish` leaves the
receiver, it has stored 0, taken its zero branch and counted the call, and it has published its untouched
copy, so the tick count stays the same. A normal call clears the zero branch again. The scenario shows fault injection through a return value; it
does not claim that the producer itself can return 0.

## HW_CI_WHO_WRITES
A write watch point on `app_state.ticks` stops the core after the write; the frame chain names
`app_receiver_step` called from `app_loop` as the writer, the stop address lies inside the writer's code
from `symbol`, `app_state` is in `.bss`, and the count advanced by one. The frame chain is recorded.
The scenario shows locating a writer; it does not cover writes by DMA or other bus masters.
On Cortex-M0 the watch point halts the core one or two instructions after the store; the receiver counts
`app_received.publications` after publishing so that the stop stays in the function body, where the frame
chain unwinds, and not in the epilogue, which carries no unwind information.

## HW_CI_RETURN_VALUE
At the entry of `app_step` the arguments carry the blink mode and a state pointer into SRAM. `finish`
returns into the receiver with the incremented count and `r0` holds the same value; after a second
`finish` leaves the receiver, it has stored the value and published it as the new count. The scenario
shows that three views of one return value agree on the AAPCS register convention.

## HW_CI_CONDITIONAL_STOP
A point at `app_step` with `ignore_count=2` stops at the third call, counted by the tick the call sees.
A new condition written to the live point selects a later call. A disabled point keeps its counter and
does not stop the core across two loop iterations; enabled again without a condition, it stops at the
next call and the counter continues. The scenario covers point control; it does not measure timing.

## HW_CI_STEP_SOURCE
Source-line steps into the receiver's call reach `app_step` within six steps, with the receiver as the
caller and the blink mode as the argument. Source-line steps over the call stay in the receiver until
its call counter advances. The scenario relies on `-Og` line information of the fixture; it does not
claim a fixed number of steps per line.

## HW_CI_UNTIL_TARGET
`until("app_receiver.c:22")` from the receiver reaches the line: the stop address is one of the resolved
targets and the produced value is stored. From inside `app_step` a target in the caller is not reached:
the producer frame exits first and the stop is back in the receiver. The line numbers belong to the
fixture source and are guarded by a host check; this is the only scenario that names a source line,
because a line location is what it checks.

## HW_CI_POINT_BUDGET
The fault guards set at boot hold slots of the profile `breakpoint_limit`; points at distinct functions
fill the remaining slots, and each lies inside its function by `symbol`. One more point is refused with
`limit_exceeded`. A disabled point frees its slot for another one, and enabling it again is refused.
`clear()` removes every point including the guards; the scenario re-arms the guards from
`profile["fault_handlers"]`, and a new point can be set afterwards. The scenario checks the software
budget; it does not probe the hardware comparators.

## HW_CI_CALL_PREDICATE
`app_state` is saved with `symbol` and `memory`, then `app_step(&app_state, mode)` is called for the idle
and the blink mode: the producer returns the incremented count, toggles the LED flag only in blink mode,
and `write_memory` restores the saved bytes after each call. The application continues from the saved
count. The scenario shows a firmware function used as a check without lasting side effects; it does not
cover functions with peripheral effects.

## HW_CI_STRINGS
The fixture firmware keeps `app_info` in Flash with a version field `char version[16]` ("v1.2.0-ci") and
a board pointer ("stm32-gdbtest-ci"), and copies the version into `app_version_ram` before the loop. At
`app_loop` the GDB string functions inside a `check(rows)` table confirm both strings (`$_streq`), the
version length (`$_strlen`), the equality of the RAM copy and the Flash bytes (`$_memeq`) and the version
prefix (`$_regex`). The same facts are then checked in Python: `evaluate(..., as_type=str)` reads the
field, the pointer and the RAM copy as text, `matches` checks the version pattern, and `memory` reads both
blocks with equal bytes. The scenario covers ASCII identification strings, not text encodings or strings
longer than the read limit.

## HW_CI_EVENT_INTERVALS
Record three intervals of 500 nominal firmware ticks with matching source, epoch, width and rate.
A host delay while halted must leave the sampled firmware counter unchanged. Invalid metadata and
ambiguous intervals are rejected by the helper; this does not establish calibrated timing accuracy.

## HW_CI_WAIT_CHANGES
Match a predicate only at the owned watchpoint, preserve unrelated points and fault guards, report
an unrelated stop without silently resuming, and exhaust a finite stop budget. Remove the owned
point on normal and exceptional exit. The budget is not a wall-clock timeout.

## HW_CI_EVENT_INJECTION
Compare natural counter wrap with forced zero return: both reach the receiver's zero branch, but
only natural execution changes producer state. Restore declared input fields on normal and
exceptional exit and verify the next normal iteration. This is not a full execution rollback.
