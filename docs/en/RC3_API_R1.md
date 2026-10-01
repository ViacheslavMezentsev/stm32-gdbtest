# rc3 R1: initial hardware API experiments

[Documentation](index.md) · [Русский](../ru/RC3_API_R1.md)

2026-10-02, Windows. Branch `codex/rc3-api-r1` continues research branch
`codex/rc3-gdb-python-research` at `9fce519`, based on main `da42cd7`.
Acceptance order: research → R1; publication/land belongs to the owner.
This is a **consumer prototype**, not a public Target API extension.
Specification0.58, API_VERSION1 and package version remain unchanged.

## Result

On **WeAct BlackPill F411CE / STM32F411CEU6**, ST-Link V2J43M28, OpenOCD0.12.0,
SWD1MHz, **48/48 hardware runs passed**: six scenarios, an initial run and three
predetermined repeats on each GDB. Both used the same GCC13.3.1 ELF, built with
`-Og -g3 -fno-lto`, Cortex-M4 and soft-float ABI.

| GDB | Embedded Python | Main scenarios |
| --- | --- | --- |
| 14.2.90.20240526-git (xPack GCC13) | 3.11.4 | 24/24 PASS |
| 16.3.90.20250906-git (xPack GCC15) | 3.13.12 | 24/24 PASS |

Each GDB also exercised an **expected serialization ERROR** and an **expected
external timeout ERROR**. All four raw reports remain ERROR; protocol PASS means
the failure assertions passed. An independent HW_R1_CONTROL passed after each.
Every hardware series restored the selected consumer firmware, passed HW_BOOT/HW_GPIO
and left the MCU in reset_run. HW_GPIO checks PC13 register transitions, not emitted light.

Experiment ELF SHA256:
`38375f4f7d58cdb637c69ae099b47c03061230a9df4eecd530475cbc96a2fd19`.
Restore ELF SHA256:
`1ff37ae10a007401de5e0eaf826764f60a2849c8b7821c123f12caa28c2e79c3`.
Evidence applies only to this board/backend/build and these operations. This package
did not test F030/F103/F401, GCC15 recompilation, IRQ/DMA/RTOS or function-call ABI.

## Consumer and scenarios

The [consumer](../../tests/api-experiments/CMakeLists.txt) is an ordinary application:
`main → process_sample → sum_bytes`, a global structure and checksum. All calls
occur naturally; no firmware test hooks or special synchronization points.
R1 enables no IRQs or peripherals. Startup/linker derive from the existing CMSIS fixture.

[Research](../../tests/api-experiments/lab/session.py) is a local GDB adapter:
restricted symbol/field/array paths instead of arbitrary eval, materialized typed
snapshots, stop epochs rejecting stale frames, RAM limited to `sample`, scoped
patches, hardware breakpoint ownership and a separate `research` JSON namespace.
The bridge uses internal Target.report; it is not a new core API. One assertion
intentionally inspects root status to test namespace isolation.

| Scenario | Demonstrated behavior |
| --- | --- |
| HW_R1_VALUES | int32/uint64/float3.5/enum/array/bounded char buffer; reject calls, assignments, invalid index and absent symbol |
| HW_R1_FRAMES | count/seed arguments, three natural frames, retained backtrace after resume, stale frame rejection |
| HW_R1_RAM | 1/2/4/8-byte writes, all other object bytes unchanged, restoration on normal exit/body exception, invalid range rejection |
| HW_R1_STOPS | Function/address/file:line; two hardware BPs at one PC, external point and four fault guards retained, location budget/missing symbol rejection |
| HW_R1_RECORD | Immutable evidence, duplicate name/>16KiB/NaN/non-JSON rejection, namespaced status cannot overwrite root status |
| HW_R1_CONTROL | Natural checksum against independent Python arithmetic and one completed cycle |

[Scenarios](../../tests/api-experiments/profile/tests/board/test_research.py),
[requirements](../../tests/api-experiments/profile/tests/requirements.md),
[host regressions](../../tests/api-experiments/host/test_session.py).
Twelve host tests include partial-write restoration, simultaneous body/cleanup
failure, external multi-location budgeting, lookup errors and empty locations,
stale frames and atomic record rejection.

## Preserved initial failure

The first run stopped with ERROR in HW_R1_STOPS: the scenario expected gdb.error
for an absent function, but GDB returned a point with no location and the adapter
raised ValueError. VALUES/FRAMES/RAM had passed; restore/boot/GPIO passed too.
The adapter now normalizes both outcomes to ValueError, with two host regressions.
The 48 successful runs form a new post-fix series; the original failure was not
deleted or silently retried until PASS.

## Evidence and checks

The [sanitized summary](../research/rc3-r1-results.json) retains stages, raw statuses,
versions, check counts and ELF/source hashes. Full local artifacts live under
`tests/api-experiments/build/evidence/`:

- `20261001T232017.946898Z`: initial ERROR and successful restoration;
- `20261001T232139.267425Z`:14 prepare +2 baseline +48 experiments +2 restore;
- `20261001T232415.062597Z`:14 prepare +2 baseline +4 expected ERROR +4 positive controls +2 restore.

Directory timestamps are UTC; local experiment date was 2026-10-02. Git excludes
serials, personal paths, local TOML, ELF and raw logs. The positive series preceded
the runner's failure-paths branch; the measured adapter and six scenarios remained
unchanged, with hashes recorded. Later the runner also gained separate primary_error
and restore_error fields; simultaneous failure of those stages was not injected on hardware.

- Windows GCC13 build and CTest host/prepare: **8/8 PASS**.
- Linux CI-image GCC13 build and CTest host/prepare: **8/8 PASS**, not Linux HW evidence.
- Formatting of all four new C/H files: PASS.
- `python3 ci/run_checks.py docs format host`: docs3/3 and host PASS; overall format
  FAIL in existing HAL code unchanged by this branch, including
  `tests/hal-f030/src/platform.c`. This is not an overall CI PASS.

## Reproduction

Configure/build with Ninja and `tests/firmware/cmake/arm-gcc.cmake` as toolchain.
Keep the build inside `tests/api-experiments/build/`: CMake/runner restrict output
directories to the consumer root. Then:

```text
cmake --build tests/api-experiments/build/gcc13
ctest --test-dir tests/api-experiments/build/gcc13 -L host --output-on-failure
python -B tests/api-experiments/run_matrix.py --session <session.json> --restore-session <restore-session.json> --stand <local.toml> --gdb <GDB14> --gdb <GDB16>
```

Without --execute, only preparation runs. With it, baseline precedes four rounds
per GDB and restoration runs in finally. For the separate expected-error series,
add `--execute --failure-paths-only`. Restoration requires a verified manifest,
F411CE profile and HW_BOOT/HW_GPIO controls. External inputs are read-only; all new
outputs stay inside this consumer. Changing board/backend requires stand agreement.

The runner sets GDB in a local session copy and compares the same ELF. Current CLI
`run --gdb` applies to --package; --session uses its own gdb field. Do not assume
the CLI flag switches both modes.

## Limits and next work

R1 demonstrates a **subset** of E01–06/E20 in the [plan](RC3_API_RESEARCH.md), not
the entire proposed API. Pending: typed NULL/unavailable/optimized-out matrix,
general read_string, shadowed locals/temporary selection, conditions/condition
errors, exit/signal/fault StopRecord classification, real-ELF multi-location and
hardware exhaustion at resume. GDB16 interrupt/inferior-call timeouts were not used;
the tested timeout is the existing runner's external deadline.

The budget conservatively counts locations; points sharing a PC may share physical
resources. This does not measure FPB capacity. All created points explicitly use
BP_HARDWARE_BREAKPOINT; next/finish/software fallback are absent. Snapshots support
simple C types and promise no DMA atomicity. RAM rollback was tested only with
the CPU stopped and no other writer, not on MMIO.

Next close the remaining R1 failure branches and define public read/snapshot/record/
StopRecord/ownership contracts. Promotion to core then requires a new specification
revision, bilingual API/migration and host regressions. R2 steps/finish/watchpoints
remain a separate experimental package.
