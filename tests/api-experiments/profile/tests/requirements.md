# R1 consumer experiment requirements

## HW_R1_VALUES
Typed initialized structure, integer/float/enum/array and bounded string; reject expressions, invalid indices and absent symbols.

## HW_R1_FRAMES
Natural nested calls, arguments and materialized backtrace; reject stale frame after resume.

## HW_R1_RAM
Bounded consumer-owned RAM reads and patches, canaries, rollback on success/body exception, reject invalid ranges before access.

## HW_R1_STOPS
Function/address/source locations, duplicate PC, external point preservation, fault guards and actual location budget.

## HW_R1_RECORD
Bounded immutable JSON evidence, duplicate/oversize/nonserializable input, namespace isolation.

## HW_R1_CONTROL
Independent arithmetic oracle and monotonic completed cycle on the normal application path.

## HW_R2_CONDITION
A one-shot conditional hardware breakpoint stops on sequence 3, deletes itself and permits source C expressions/convenience variables.

## HW_R2_HITCOUNT
Ignore two entries, identify the third, recognize immediate/outer/wrong callers and separately report built-in caller function availability.

## HW_R2_RETURN
Forced return supplies 100 to the natural caller and changes its independently checked checksum.

## HW_R2_FINISH
FinishBreakpoint captures the natural uint32 return and selects the caller; backend enforces hardware-only insertion.

## HW_R2_STEP
Instruction stepping advances PC; bounded source step enters sum_bytes, finish returns, next skips child frames.

## HW_R2_WATCH
CPU write/read/access watchpoints use hardware types, produce expected stop identities and are deleted between trials.

## HW_R2_CALL
Direct invocation of a pure existing function yields 775 and restores PC/SP while preserving the input object.

## HW_R2_ASM
Jump to the existing default handler, recognize Thumb b-to-self via bytes and disassembly, confirm fixed PC with stepi, then reset to main.

## HW_R3_COMMANDS
Breakpoint command list intercepts one call, forces a return and resumes to a verified sentinel; commands after continue are skipped and later calls execute naturally.

## HW_R3_DEADLINE
A hardware watchpoint on an unsigned progress predicate stops after three completed cycles, including counter wraparound; it is not a wall-clock timeout.

## HW_R3_SAMEVALUE
A natural CPU store of an unchanged checksum is suppressed by write-watch and detected by access-watch, with a separate sentinel proving progress.

## HW_R3_LANGUAGE
Source-context C macros, parameterized GDB branching, quoted semicolons and failure-short-circuiting command sequences work on the target debugger.
