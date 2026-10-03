# Research plan

[Research](index.md) · [Русский](../ru/plan.md)

## Baseline and boundaries

The compatibility baseline is v0.1.0-rc.2, commit
`a0d6547ba83b7c911f8f3028cb064aeedd3e5a36`.
The working tree baseline is recorded in the [research index](index.md).
Original scenarios remain available for comparison; signatures below are provisional.
Prototypes will live separately in `tests/api-extension` once implementation starts;
they must not replace Target, the runner or the installed package.

## Candidates and intended benefit

| Stage | Candidate | Existing scenario and intended benefit |
| --- | --- | --- |
| E1 | `record(name, data)` | [ADC](../../../../tests/firmware/profiles/f411ce/tests/board/test_adc.py), [HAL runtime](../../../../tests/hal-f030/hal_scenarios/peripheral_runtime.py): replace direct report writes with an evidence contract |
| E2 | Bounded typed `read` | Same scenarios: read arrays and selected fields without repeated value calls; define size and depth limits |
| E3 | `frames` and minimal `context` | [Sleep/WFI](../../../../tests/firmware/profiles/f411ce/tests/board/test_sleep.py): remove direct GDB frame traversal while preserving interrupted-context recognition |
| E4 | `finish` | [HAL methods](../../../../tests/hal-f030/profile/tests/board/test_hal_methods.py): check effects immediately after a natural return |

For each stage: describe its experimental contract and negative cases, implement an
isolated prototype and compare scenarios, then produce a separate report.
Snapshots and events must be materialized, serializable and bounded in size;
results must not contain live GDB objects. All GDB calls run on its main thread.

- E1: define duplicate names, entry ordering, invalid values and size limits;
  recording errors must not hide the original FAIL/ERROR.
- E2: missing symbols, optimized-out values, memory errors, arrays/structures,
  field selection and limits; prohibit implicit function calls. Reads do not
  promise atomicity with running DMA. Existing integer value semantics remain unchanged.
- E3: stack end, depth limit, unwind error, unnamed and signal frames, snapshot
  freshness after resuming. An incomplete stack does not establish caller absence.
  Caller search and interrupted-frame selection remain techniques.
- E4: normal return, void/scalar, unavailable value, another breakpoint, fault,
  timeout, hardware breakpoint exhaustion and cleanup. Do not promise unverified
  ABIs/aggregates. Preserve fault guards and external timeout/recovery.

## Comparison and criteria

1. Preserve original and experimental variants, map every assertion and retain
   independent expected values. Fewer assertions are not an improvement.
2. Compare scaffolding lines, direct GDB/report accesses, diagnostic data and
   negative outcomes. Count prototype lines separately from scenario lines.
3. Check contracts with controlled host failures; these tests do not establish
   actual unwind, ABI, breakpoint or MMIO behavior.
4. After resuming hardware work, compare variants on the same ELF and settings.
   Start with F411, then check F030/F103/F401 portability; F429 when a bench is available.
   Record MCU, GDB, backend, optimization, ABI, ELF/manifest hashes and halt/reset effects.
5. For finish, account for the changed observation point: HAL return and a later
   application checkpoint establish different properties. Keep both if removing
   either weakens the scenario.

Each stage receives a separate RU/EN `eN.md` report; sanitized JSON goes in
`results/`, linked from its report and registry. Preserve original FAIL/ERROR
outcomes instead of replacing them with successful retries. Do not commit raw
logs, ELF files or local TOML configurations.

## Outside the first package

Watchpoints, GDB function calls, arbitrary PC writes, universal MMIO rollback,
RTOS and advanced assembly operations are outside E1–E4. Counter arithmetic,
ranges and MCU-specific expectations remain consumer techniques.
The study produces an API scope recommendation and limitations, followed by separate
approval of conventions/API specification and core integration; no release target is implied.
