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

## HW_R4_NATURAL
Natural output-buffer call fills eight bytes and returns their count; caller computes an independent total and preserves packet metadata.

## HW_R4_OUTPUT
Replace a bounded output buffer and force success; natural caller consumes the supplied data, then the next call resumes normal behavior.

## HW_R4_ERROR
Supply poison output bytes and force a negative status; caller records the error without accepting the buffer, and the next natural call recovers.

## HW_R4_SHORT
Supply a short-packet status with poison tail; caller rejects the incomplete packet without accumulating its bytes, then recovers naturally.

## HW_R5_WIDE_FINISH
Verify WIDE FINISH against an independent value and natural caller sink, then confirm the next normal call.

## HW_R5_WIDE_RETURN
Verify WIDE RETURN against an independent value and natural caller sink, then confirm the next normal call.

## HW_R5_WIDE_CALL
Verify WIDE CALL against an independent value and natural caller sink, then confirm the next normal call.

## HW_R5_FLOAT_FINISH
Verify FLOAT FINISH against an independent value and natural caller sink, then confirm the next normal call.

## HW_R5_FLOAT_RETURN
Verify FLOAT RETURN against an independent value and natural caller sink, then confirm the next normal call.

## HW_R5_FLOAT_CALL
Verify FLOAT CALL against an independent value and natural caller sink, then confirm the next normal call.

## HW_R5_STRUCT_FINISH
Verify STRUCT FINISH against an independent value and natural caller sink, then confirm the next normal call.

## HW_R5_STRUCT_RETURN
Verify STRUCT RETURN against an independent value and natural caller sink, then confirm the next normal call.

## HW_R5_STRUCT_CALL
Verify STRUCT CALL against an independent value and natural caller sink, then confirm the next normal call.

## HW_R5_STRUCT_SRET
A reviewed ELF and exact entry prove the hidden return slot; bounded stack-buffer substitution plus bare return reaches the caller, preserves neighbors and restores natural behavior.

## HW_R6_CONTEXT
Read-only Python stop filtering distinguishes equal-depth recursive calls by ancestry and arguments; native caller predicate agrees and ignored calls run naturally.

## HW_R6_FINISH
FinishBreakpoint tracks a selected recursive invocation despite repeated return addresses; return value, caller arguments, PC and SP identify the correct frame.

## HW_R6_RETURN
Force return only from the selected beta recursive frame, verify remaining caller additions, unchanged alpha and subsequent natural execution.

## HW_R7_WIDTH
Characterize aligned 1/2/4/8-byte and unaligned 2/4-byte hardware read ranges; retain insertion rejection and verify independent post-trial write-watch control.

## HW_R7_CAPACITY
Probe one through eight bounded static word watches, stop on explicit insertion rejection, preserve observations and confirm a fresh hardware write-watch after cleanup.

## HW_R7_SPLIT
Split exact unaligned ranges into aligned hardware read points; verify each expected byte access and reach a sentinel before a second reader.
