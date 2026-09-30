# F030 HAL regression preservation plan

[Documentation](index.md) · [Русский](../ru/F030_HAL_REGRESSION.md)

Fixture/CI/HW stages are in main `7f3c65b`; consumer integration is `a48c944`.
See [hardware acceptance](F030_HAL_VALIDATION.md); stage history is retained below.

Stage record: case counts and plans below refer to the stated revision.
Current scope: [STATUS](STATUS.md); release preparation: [rc.2](RC2_READINESS.md).

Preparation following the [HAL → CMSIS comparison](F030_CMSIS_ACCEPTANCE.md).
The standalone build and17 scenarios are implemented in tests/hal-f030.
This is an offline migration, not a new HW PASS. Specification0.38,8.32/TC-129;
API and schemas are unchanged.

## Source baseline and location

Source: [stm32-hwtest-blackpill, 0c8c966](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/tree/0c8c966f0429710e6e20472fbd9fe8898da7cfee).
Keep a separate `tests/hal-f030` fixture outside CMSIS `tests/firmware` and the
core. Initially retain all17 scenarios so firmware simplification cannot
silently change the evidence. Reduction is a later step.

| Consumer source | Purpose in the migration |
| --- | --- |
| profiles/f030r8/Core, Platform, linker and IOC | Startup, initialization and adapter; IOC records provenance, CI does not require CubeMX |
| User/Inc/app.h, User/Src/program.cpp, adc_units.cpp | Existing loop, state and error handling; initially without redesign |
| profiles/f030r8/target.toml and tests/ | Identity, contracts, expectations, requirements and two scenario files |
| tests/scenarios/board.py, peripheral_runtime.py, power.py | Only F030 scenarios in use; no imports from the source repository |
| LICENSE and source notices | Preserve application MIT license and the notices/licenses of ST components |

Fixture CMake explicitly lists sources and consumes HAL/CMSIS from pinned
CubeF0 1.11.6. No stm32-cmake-yml dependency, absolute consumer paths or downloads
during offline checks. Do not copy ST libraries into the core. Separate build,
ELF and manifest; `-Og -g3`, no LTO. New owned directories use lowercase.

## Evidence to preserve

| Original profile scenarios | Preservation criterion |
| --- | --- |
| HW_CLOCK, HW_GPIO, HW_BLINK | HAL/CMSIS expressions available in selected DWARF context check actual state; do not replace all checks with numeric masks |
| HW_ADC_DMA_INIT | hadc/hdma_adc fields and independent register expectations, scan16/17, normal halfword DMA |
| HW_TIM3_INIT | PSC7999, ARR99 and CEN=0 before start; checking an already running CMSIS timer is not equivalent |
| HW_ADC_DMA_RUNTIME | Two callbacks, correct hadc pointer, exhausted DMA and two published sequences |
| HW_TIM3_IRQ, HW_RTC_ALARM | Natural events, correct callback handles, counters and publication |
| HW_ADC_START_ERROR | force_return HAL_ERROR from HAL_ADC_Start_DMA → Error_Handler, no published sequence |
| HW_ADC_DMA_TIMEOUT | force_return void from callback after DMA completion → deadline/Error_Handler; suppressed publication, not a DMA fault |
| HW_BOOT, HW_RTC_INIT, HW_ADC_UNITS, HW_ADC_INVALID, HW_ADC_VECTORS, HW_SLEEP_SYSTICK, HW_SLEEP_TIMER | Retain original checks as migration controls; no sensor accuracy or power measurement claim |

Original HAL case names may stay: separate CMake builds/sessions isolate them
from CMSIS. No test hooks, synthetic HAL functions, replacement handles or
special firmware branches for tests. Recheck contracts against real ELF types
and macros after migration. New source-review hashes require a separate review
of the HAL sources.

## Branch sequence

1. `codex/f030-hal-regression-plan` from `cea01f9`: this scope and acceptance plan.
2. Planned `codex/f030-hal-fixture`: standalone build, provenance/licenses,
   all17 scenarios, manifest/trace/prepare; new specification requirements and TC.
3. Planned `codex/f030-hal-ci`: integrate the fixture into offline CI with an
   explicit inventory; positive and negative contract checks. Linux and Windows,
   GCC13 first; do not claim GCC14/15 validation beforehand.
4. Planned `codex/f030-hal-validation`: hardware protocol and migration readiness
   decision after addressing all observed errors.

Branches2–4 depend on predecessors; record exact bases when created. Publish a
batch after local checks; verify Docs/Offline for each SHA, then land in order.
The plan itself needs no firmware rebuild. Update the consumer gitlink after
accepting the batch. Do not remove its old HAL profile yet.

## Acceptance

- Build from a separate module checkout without the source consumer; its paths
  must not appear in the manifest. CI requires exactly17 prepare cases,
  traceability and contract verification; a missing test is an error.
- Import Python scenarios separately on case-sensitive Linux: AST collection
  does not prove import resolution. Invalid contracts fail before the server.
- HW: NUCLEO-F030R8, native ST-Link, SWD, OpenOCD;17/17 on the migrated ELF,
  JSON/JUnit per case, exact SHA/GCC/HAL/backend and evidence limits.
- After both injections, separately repeat normal ADC, TIM and RTC; check the
  standard runner timeout/recovery and restoration. Preserve the first error,
  do not hide it through automatic retries. Follow the established stand
  confirmation procedure before the suite; no board change is needed now.
- Restore the existing consumer HAL firmware and reset_run at the end.
  The new ELF does not inherit previous hardware PASS results.

Removing the consumer HAL profile is a separate decision after publication,
CI and hardware acceptance. This fixture preserves module mechanisms on F0;
it does not replace F1/F4 HAL differences or the future F411 consumer regression.

[Techniques catalogue TECH-001…008](TESTING_TECHNIQUES.md) — stable scenario references, build prerequisites, limits and restoration. Preserve TECH-001/003/004 references when migrating HAL scenarios.

## Implemented offline stage (2026-10-01)

Branch codex/f030-hal-fixture from main69cfb79. [Fixture and commands](../../tests/hal-f030/README.en.md).
Core/startup/linker and application firmware are preserved; Python helpers are
local to hal_scenarios, with unused F1/F4 rcc_error omitted. TECH-001/003/004/007
reference the guide. Provenance records the original SHA, paths and LF-normalized
hashes; previous hardware results are not inherited.

Windows GCC13: build and CTest19/19 (17 prepare + trace + fixture) PASS;
docs/format/host5/5 PASS (host97,8 skips). Linux GCC13: isolated module snapshot
without the consumer, build and CTest19/19 PASS, docs/host4/4 PASS.
Reports: module build/hal-fixture-check. The local Linux image lacks clang-format:
the initial format ERROR is recorded in the work history. Format was checked
with Windows clang-format; Linux format is not claimed PASS. Original ST/CubeMX
whitespace is preserved, so git diff --check reports existing whitespace in imports.

General CI does not build the HAL fixture yet: the next CI branch adds an exact
inventory and negative contracts. HW17/17, positive repeats after injections and
timeout/recovery remain untested. The consumer HAL profile has not been removed;
the connected board firmware was not changed.

## CI stage (2026-10-01)

codex/f030-hal-ci from a3898ff adds the mandatory hal level to Offline.
[Checks and local invocation](testing.md#f030-hal-in-offline-ci).
HAL F0 uses the CubeF0 gitlink:0cf0218694f30a90d11ff9e53c1908bf9e745443.
The new pinned Docker image built successfully and passed environment verification.
An isolated Linux filesystem, network disabled: full15/15 PASS — docs3 + format1 +
host1 + CMSIS9 + HAL1. HAL:19 CTest,17 fresh prepare JSON reports, positive preflight
and5 negative contracts. Windows docs/format/host/hal6/6.
Specification0.39/TC-130; core API/runtime unchanged.

Module evidence: build/hal-ci-check/ci/summary.json, hal-results/ci.log,
hal-results/junit.xml, hal-results/contracts/*.result.json; image build: build/hal-ci-image.log.
GitHub CI for this SHA remains required after push. No new HW run was performed.
Previous a3898ff passed Docs and all5 Offline jobs before HAL CI was added.
The earlier statement that general CI does not run the fixture describes stage0.38.
