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

## HW_R8_CAPACITY
Probe distinct hardware code locations while preserving four fault guards; retain insertion rejection, release owned points and continue without reset.

## HW_R8_FINISH
Exhaust code-point headroom, observe FinishBreakpoint insertion rejection, release one owned point and verify the original natural return and caller result without reset.

## HW_R9_RESUME
Identify a breakpoint-interrupted inferior call and its dummy frame; resume without reset, verify restored registers and RAM, then obtain a result from a fresh call and confirm natural execution.

## HW_R9_INTERCEPT
Force an error from a nested function inside a dummy call, resume the outer call, verify register restoration and persistent caller RAM effects, then confirm a normal call and natural execution.

## HW_R10_FAULT
Retain ERROR for a CPU read past F411 SRAM during an inferior call; identify HardFault guard, active exception, precise BusFault address and dummy frame before reset_run teardown.

## HW_R10_TIMEOUT
Retain ERROR for a non-returning inferior call; persist entry into the thread-mode dummy loop, enforce external host timeout and confirm host recovery.

## HW_R10_CONTROL
After each expected error, verify reset-cleared fault status, thread mode, a fresh inferior call and normal application checksum.

## HW_R11_SYSTICK
On the CMSIS F411 ELF, identify natural SysTick context, compare the GDB unwind with the hardware exception stack, read interrupted locals with selection restoration and verify natural exception return and application progress.

## HW_R11_TIM2
On the CMSIS F411 ELF, identify natural TIM2 context and its interrupted delay, verify the basic MSP exception stack and actual restored registers, timer work and subsequent application progress.

## HW_R12_WRITE
Observe DMA buffer mutation without a reported write-watch stop before the exact completion-handler entry; verify transfer state, a CPU write-watch control and normal consumer results on the CMSIS F411 ELF.

## HW_R12_ACCESS
Observe DMA completion independently of an access watch, then prove that the same watch detects the CPU reading the DMA buffer; verify consumer values and absence of ADC errors.

## HW_R13_SYSTICK
Find WFI in the CMSIS delay function, isolate SysTick wakeups, observe a post-WFI exception frame and natural return, restore IRQ enable masks and confirm delay completion.

## HW_R13_TIM2
Isolate TIM2 with SysTick disabled, verify WFI/IRQ/return without advancing the delay timebase, restore enable/control bits and confirm eventual delay completion.

## HW_R14_SEQUENCE
Intercept consecutive natural packet reads with two errors followed by success; verify arguments, projected call order, counts, caller consumption and natural behavior after removing interception.

## HW_R14_RETAIN
Verify that an error and a short packet preserve the last accepted total across a finite interception sequence, followed by a natural successful read.

## HW_R14_ORDER
Reject an intentionally wrong call-order expectation at a real target stop without consuming it or modifying the target, then verify normal execution.

## HW_R15_LOCATIONS
Reject an ambiguous location through the single-location adapter, then observe both inline instances with one raw hardware breakpoint within the physical location budget, verifying frames, arguments and final outputs.

## HW_R15_VALUES
Observe local-value availability across one machine instruction in optimized inline code; reject optimized-out snapshots and verify natural caller results.
