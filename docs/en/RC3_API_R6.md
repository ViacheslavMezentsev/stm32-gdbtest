# rc3 R6: call context and recursive frames

[Documentation](index.md) · [Русский](../ru/RC3_API_R6.md)

2026-10-02. Continuation of [R5](RC3_API_R5.md) after `191244d` on
`codex/rc3-api-r1`. Consumer only; public API, specification and package version
unchanged. Core promotion requires separate owner approval.

## Task and techniques

Two ordinary handlers call the same recursive `walk_route(depth,seed)` function.
Each level increases seed by10 and adds depth on return. `route_alpha` starts
with(2,1) and adds100; `route_beta` starts with(3,2) and adds200. The scenario
independently checks natural results124 and238. There are no new hooks; this code
runs in the normal application loop.

| Trial | Verified behavior |
| --- | --- |
| CONTEXT | Python `Breakpoint.stop()` reads frames and arguments; selects depth1 only with `route_beta` at caller depth3. Alpha/depth1 has seed11, beta/depth1 has seed22. `$_caller_is` confirms the stack; incorrect depth is rejected |
| FINISH | At beta/depth2, FinishBreakpoint survives nested calls with repeated return addresses and captures35. It then verifies caller name, depth3, seed2, PC and SP |
| RETURN | `return 100` at beta/depth1 yields305 through remaining callers. Alpha remains124; the next natural cycle restores beta238 |

[Scenarios](../../tests/api-experiments/profile/tests/board/test_recursion.py),
[ordinary functions](../../tests/api-experiments/src/routes.c).

## Corrected assumption

The first version combined `bp.condition = 'depth == 1'` with Python `stop()`,
expecting only two callback invocations. Instead the callback saw six entries with
seeds1,11,21,2,12,22. It selected the intended context, but the visit-count assertion
failed on GDB14. The original FAIL is retained; the series stopped and firmware
was restored. This was a scenario assumption error, not an established GDB defect.

All selection conditions now reside in one Python predicate. The full depth
sequence2,1,0,3,2,1 is verified, with five rejections and one selection. Separately,
FINISH/RETURN use only a CLI condition with `$_caller_is`, without a Python callback.
Do not assume that condition expressions prefilter all custom `stop()` invocations;
this experiment does not generalize the ordering of that combination.

## Applications and limits

- Intercept a shared function only from a chosen handler, distinguish recursive
  levels and supply a result to a selected caller.
- A function name or return address alone does not identify a recursive frame.
  This experiment uses ancestry, arguments and PC/SP; FinishBreakpoint is checked
  by its own breakpoint event and the independent expected value35.
- Callbacks only read GDB state and collect Python data: no continue, breakpoint
  deletion, frame selection or memory writes. Mutations happen after control
  returns to the scenario.
- A rejected Python predicate is not invisible to the MCU: debugger stops affect
  execution time. This experiment does not measure real-time behavior.
- Only shallow recursion, ordinary C stacks and GCC13 `-Og -fno-lto` were tested.
  IRQ, RTOS, inline/tail-call, corrupt stacks and callback exceptions remain untested.

## Reproduction and results

F411CE/ST-Link/OpenOCD0.12.0 HLA, Windows; GDB14 and GDB16. GCC13 soft-float ELF:
`7842e8ee9471ec777001a1fcc5be6e4a9625af3883eee7c8a1b15ebbcd6c5552`.
SWD frequency is not assumed constant: reset logs may override the stand setting,
as noted in R5.

**Corrected R6:24/24 HW PASS**,12 per GDB version. The initial FAIL belongs
to the earlier callback assumption and is not replaced by a retry.
Windows/Linux build/host/prepare:37/37 PASS (35 prepare, traceability and20 host
tests grouped together); affected C format PASS. The prior overall format FAIL remains.

Selected regression on the new ELF/GDB16/HLA: eight positive R5 ABI scenarios,
32/32 PASS. A separate run of the old SRET produced the expected SHA256-check FAIL
before return-buffer writes; the guard was not bypassed and the pin was unchanged.
This is not a supported-SRET regression: the new ELF lies outside its applicability.
All four series completed restore HW_BOOT/HW_GPIO PASS. Full R1–R5, Linux HW,
native DAP for R6 and other boards were not tested.

Add `--suite r6` to the [R1 command](RC3_API_R1.md#reproduction).
Three scenarios × initial run plus three predetermined repeats × two GDB versions.
Without `--execute`, preparation only. The [sanitized protocol](../research/rc3-r6-results.json)
retains the initial FAIL, corrected series, selected regression and restoration.
Raw logs remain in `tests/api-experiments/build/evidence/`.

The new ELF intentionally does not match the old SHA256 pinned by R5 SRET. Do not
automatically repin that prototype: first review the new disassembly and result
buffer placement. Historical R5 PASS applies to the earlier ELF.
