# rc3 R5: return types and ARM ABI

[Documentation](index.md) · [Русский](../ru/RC3_API_R5.md)

2026-10-02. Continuation of [R4](RC3_API_R4.md) after `2c6c8a6` on
`codex/rc3-api-r1`. Consumer changes only; public API, specification and package
version unchanged. Core promotion requires owner approval.

## Comparison

An ordinary handler calls three functions from a separate translation unit and
saves their results. Interprocedural optimization is disabled. Scenarios compare
the GDB value, caller result and subsequent natural call.

| Type | Natural result | Forced substitution |
| --- | --- | --- |
| `uint64_t` | `0x123456789abcdef9` | `0xfedcba9876543210` |
| `float` | `4.75` | `-2.5` |
| `struct ReturnPair` (8 bytes) | `{code:-8,count:20}` | `{code:-7,count:19}` |

Operations: `FinishBreakpoint.return_value`, CLI `return <value>` and direct calls
through `gdb.parse_and_eval`. Direct calls also verify PC/SP and preservation of
the sample object. Float values are exactly representable; NaN/Inf, rounding,
double, hard-float, void and C++ were not tested.

[Main scenarios](../../tests/api-experiments/profile/tests/board/test_return_types.py),
[ordinary functions](../../tests/api-experiments/src/returns.c).

## Why a successful return command is insufficient

On both versions, `return pair_input` selected the caller without a GDB exception,
but the caller received `{-8,20}` instead of `{-7,19}`. Both original FAIL reports
are retained; the runner stopped each series and restored firmware. Absence of
an exception does not establish successful substitution. Old return-buffer bytes
do not prove that the function body executed.

In this ELF, `process_returns` passes a temporary result address in `r0`, then
reads that buffer through saved `r4`. `transform_pair` writes two fields through
`r0`. This matches the memory return of a composite type larger than4 bytes in
[ARM AAPCS32](https://github.com/ARM-software/abi-aa/blob/main/aapcs32/aapcs32.rst#result-return).
The experiment does not establish the internal cause in the particular GDB build.

## Alternative technique: return buffer

A [separate scenario](../../tests/api-experiments/profile/tests/board/test_sret.py)
stops exactly before the prologue and checks ELF SHA256, caller, structure size8,
`r0 == sp`, alignment and SRAM bounds. After recording intent, it writes eight
bytes, checks four adjacent bytes on each side, executes a bare `return`, and
checks the caller result. The following natural call must yield `{-8,20}` again.

This technique targets a reviewed ELF, not a universal `return_struct` adapter.
The buffer need not equal SP in other code; after the prologue `r0` may already
have changed. These assumptions do not transfer to other structures, ABIs or
optimization settings. Do not roll back the buffer before the caller reads it.
The scenario deliberately rejects another ELF before writing memory.

## Results

| Operation | uint64_t | float, soft-float | 8-byte structure |
| --- | --- | --- | --- |
| FinishBreakpoint | 8/8 PASS | 8/8 PASS | 8/8 PASS |
| return value | 8/8 PASS | 8/8 PASS | FAIL on GDB14 and GDB16 |
| Direct call | 8/8 PASS | 8/8 PASS | 8/8 PASS |
| Buffer + bare return | — | — | 8/8 PASS |

Each positive cell includes an initial run and three predetermined repeats on
each GDB version:64/64 for the main positive matrix and8/8 for SRET. Seven GDB14
scenarios also passed in the original interrupted series; they are not counted
in64/64. The two original FAIL reports are not replaced by positive results.

Windows/Linux build/host/prepare: **34/34 PASS**, comprising32 prepare, traceability
and20 host regressions grouped into one test; affected C format PASS. The earlier
overall format FAIL remains. Selected new-firmware regression on GDB16/native DAP:
R4 —16/16, R3 DEADLINE/SAMEVALUE —8/8. This is not a full R1–R4 regression.
All six series completed restore HW_BOOT/HW_GPIO PASS. R5 used HLA; Linux HW and
other boards were not tested.

## Reproduction and evidence

F411CE/ST-Link/OpenOCD0.12.0 HLA, Windows; GCC13 `-Og -g3 -fno-lto`, soft-float.
ELF `db27a41c0115eb83d0a7a808b6f68d59098ec20be91f98b1a9a48ae10e6abe0e`.
The local stand requests SWD1000kHz, but reset logs report a2000 request and1800kHz
selection; a constant actual1000kHz rate is not asserted here.

Add `--suite r5` to the [R1 command](RC3_API_R1.md#reproduction).
The full set deliberately retains diagnostic STRUCT_RETURN, which produces FAIL.
For the positive matrix, list eight `--test HW_R5_<TYPE>_<MODE>` arguments excluding
STRUCT_RETURN; run SRET separately with `--test HW_R5_STRUCT_SRET`.
Without `--execute`, only preparation runs.

The [sanitized protocol](../research/rc3-r5-results.json) retains original FAILs,
positive series, versions, source SHA256 and restoration results. Full logs remain
in `tests/api-experiments/build/evidence/`. Adding SRET changes the scenario
inventory, not the ELF; original reports are not replaced. Previous results retain
their own ELF identities and are not automatically revalidated on the new firmware.
