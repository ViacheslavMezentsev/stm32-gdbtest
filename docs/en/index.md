# stm32-gdbtest documentation

Documentation · [Русский](../ru/index.md)

stm32-gdbtest implements [DDTT](DDTT.md) for STM32: scenarios in the project repository check
running firmware on a real board through GDB and an SWD debugger. Introduction — [README](../../README.en.md);
requirements — the [specification](../TECHNICAL_SPECIFICATION.md) and the
[API specification](../TECHNICAL_SPECIFICATION_API.md) (Russian only). Skills for AI agents and TTDD
routes — [skills](../../skills/README.en.md). Where a page exists in both languages, Russian is the source.

## Getting started

- [Getting started](GETTING_STARTED.md) — requirements, checks without a board, submodule integration.
- [Writing tests](TEST_AUTHORING.md) — the process for people and AI agents.
- [Scenario checklist](SCENARIO_CHECKLIST.md) — review before a run, before changing state and after the experiment.
- [Stepping through a scenario](MANUAL_DEBUG.md) — `run --interactive`: breakpoints and the Debug Console in VS Code with no time limit.
- [Run layouts](RUN_LAYOUTS.md) — placement of runner, GDB and probe, verified combinations.
- [MCU profiles](MCU_PROFILES.md) — target.toml and verified boards.
- [Stands](STANDS.md) — stand boards: summary and schematic top views.
- [DDTT specification](DDTT.md) — the method: terms, principles, requirements for scenarios, stands and tools.

## Scenarios and API

- [API, CLI and migration](API.md) — CMake, the `case` decorator, Target API, `run`, migrating from hwtest.
- [Methods reference](api/index.md) — every Target method with its first release and examples.
- [Techniques catalogue TECH-001…027](TESTING_TECHNIQUES.md) — stable techniques referenced from scenarios, prerequisites and restoration.
- [Live execution window](LIVE_EXECUTION.md) — `async def`, `resume(sync=False)`, `await wait/halt`; contract and migration.
- [VTOR/FPB observer](LIVE_OBSERVER.md) — a neutral live-window example, oracle and cleanup.
- [MMIO registers](MMIO.md) — known limitations and the recommended validation route.
- [SVD](SVD.md) — peripheral description for `t.mmio`, capture into the package and limits.
- [ELF/HAL contracts](CONTRACTS.md) — offline checks of functions, types, enums and source hashes.
- [HAL macros](../guides/en/HAL_MACRO_GUIDE.md) — choosing macros, context and the macro contract.
- [Moving to 0.5.0](MIGRATION_050.md) — consumer migration to API 3.
- [CMSIS example migration](../guides/en/CMSIS_MIGRATION.md) — baseline, F030 gaps and acceptance.

Neutral examples: [simulated input: write and ret](../../tests/controlled-input/README.en.md) ·
[modeled GPIO](../../tests/modeled-gpio/README.en.md) · [buffer and repeated consumption](../../tests/buffer-consumption/README.en.md) ·
[C++ context](../../tests/cpp-context/README.en.md) · [C++, cache and deferred writes in Renode](../../tests/renode-cache/README.en.md) ·
[residual state and ring](../../tests/stateful-buffer/README.en.md) · [logical time](../../tests/logical-time/README.en.md) ·
[counters and observation cost](../../tests/counter-cost/README.en.md) · [joint capture](../../tests/external-capture/README.en.md) ·
[ROS1 bag import](../../tests/rosbag-import/README.en.md) · [live-window observer](../../tests/live-observer/README.en.md).

## Results, journal and DDTT

- [Journaling](JOURNALING.md) — sources, quotas, completeness, error/truncate policies.
- [Result export](RESULTS.md) — evidence index, CSV/HTML and integrity checks.
- [DDTT in VS Code](DDTT_COVERAGE.md) — source colouring from check evidence.
- [Portable DDTT](PORTABLE_DDTT.md) — a public report bound to a revision, without local data.
- [Condition qualification](DDTT_QUALIFICATION.md) — raw outcomes separate from admission and final colouring.
- [Verification metrics](HARDWARE_METRICS.md) — how to read outcome counts and what they are not.

## Stands, GDB servers and CI

- [GDB servers](../guides/en/BACKENDS.md) — OpenOCD, ST-LINK GDB Server, J-Link, st-util: [OpenOCD](../guides/en/backends/openocd.md) ·
  [ST-LINK GDB Server](../guides/en/backends/stlink.md) · [J-Link](../guides/en/backends/jlink.md) · [st-util](../guides/en/backends/st-util.md).
- [Debugger ownership](../guides/en/DEBUGGER_OWNERSHIP.md) — cross-project locking on Windows and Linux.
- [Linux stand](../guides/en/LINUX_STAND.md) — environment without root, USB, J-Link, remote GDB server over SSH, WSL2.
- [Hardware CI](../guides/en/HARDWARE_CI.md) — prepared run packages, a self-hosted runner, 24/7 runs.
- [Stand loop](STAND_LOOP.md) — a finite plan of accepted packages, attempts, STOP and SKIP.
- [HIL link check](HIL_INSPECT.md) — HIL, backend and SVD without starting tools.
- [MCU identity](TARGET_IDENTITY.md) — DEV_ID and the factory Flash size.
- [Images and CRC](IMAGES.md) — ELF sections, BIN, full image and the Flash check range.
- [Manifest](MANIFESTS.md) — compatibility and build provenance metadata.
- [Compatible MCUs](../guides/en/COMPATIBLE_MCU.md) — Cortex-M from other vendors (AT32): profile, CMSIS, scenarios.
- [Checks and CI](../guides/en/testing.md) — CI levels, Docker image, hardware check of the CI firmware.
- [Local CI](../guides/en/local-ci.md) — Docker and L6: snapshot, volume, evidence and stand restoration.

## Emulators

- [Renode](../guides/en/RENODE.md) — configuration, one process per scenario, model limits.
- [QEMU](../guides/en/QEMU.md) — configuration and limits.
- [Renode probes](../guides/en/RENODE_PROBES.md) — short experiments on the model and their limits.

## Board evidence

Summaries: [accepted API and results](../evidence/en/API_ACCEPTANCE.md) · [five-profile CMSIS acceptance review](../evidence/en/CMSIS_ACCEPTANCE.md).

- **F030:** [CMSIS baseline](../evidence/en/F030_CMSIS_BASELINE.md) · [TIM3/IRQ](../evidence/en/F030_CMSIS_TIMER.md) · [ADC/DMA](../evidence/en/F030_CMSIS_ADC_DMA.md) ·
  [ADC units](../evidence/en/F030_CMSIS_ADC_UNITS.md) · [busy ADC](../evidence/en/F030_ADC_BUSY.md) · [Sleep/WFI](../evidence/en/F030_CMSIS_SLEEP.md) ·
  [RTC](../evidence/en/F030_CMSIS_RTC.md) · [RTC deadline](../evidence/en/F030_RTC_DEADLINE.md) · [HAL→CMSIS mapping](../evidence/en/F030_CMSIS_ACCEPTANCE.md) ·
  [HAL: GPIO/RCC](../evidence/en/F030_HAL_GPIO_RCC.md) · [HAL regression](../evidence/en/F030_HAL_REGRESSION.md) · [HAL hardware acceptance](../evidence/en/F030_HAL_VALIDATION.md).
- **F103:** [clocks/GPIO/SysTick/TIM2](../evidence/en/F103_CMSIS_BASELINE.md) · [ADC/DMA](../evidence/en/F103_CMSIS_ADC_DMA.md) · [RTC/Sleep](../evidence/en/F103_CMSIS_RTC_SLEEP.md).
- **F401:** [clocks/GPIO/SysTick/TIM2](../evidence/en/F401_CMSIS_BASELINE.md) · [ADC/DMA](../evidence/en/F401_CMSIS_ADC_DMA.md) · [RTC/Sleep](../evidence/en/F401_CMSIS_RTC_SLEEP.md).
- **F411:** [clocks/GPIO/SysTick/TIM2](../evidence/en/F411_CMSIS_BASELINE.md) · [ADC/DMA](../evidence/en/F411_CMSIS_ADC_DMA.md) · [RTC/Sleep](../evidence/en/F411_CMSIS_RTC_SLEEP.md).
- **F429:** [clocks/GPIO/SysTick/TIM2](../evidence/en/F429_CMSIS_BASELINE.md) · [ADC/DMA](../evidence/en/F429_CMSIS_ADC_DMA.md) · [RTC/Sleep](../evidence/en/F429_CMSIS_RTC_SLEEP.md).

These are historical acceptance stages: counts belong to their revisions; the current state is in [STATUS](STATUS.md).

## Releases and maintenance

- [Current status](STATUS.md) — version, verified scope, stands and limits.
- [Versions and releases](VERSIONING.md) — SemVer, tags, moving between releases.
- [Release transitions](RELEASE_CHANGES.md) — what changes for users and what to do.
- [0.6.0 release notes](../releases/v0.6.0.md) · [0.6.0 acceptance matrix](../development/release-060-acceptance.md) (Russian) ·
  [0.5.0 acceptance](../development/release-050-acceptance.md) (Russian) · [CHANGELOG](../../CHANGELOG.en.md).
- [Maintenance](../guides/en/maintenance.md) — workflow, branches, commits, bilingual documentation.
- [HOWTO](../guides/en/HOWTO.md) — git commands (including `git land`), common stand, debugger and Docker problems.
- [Documentation structure](../development/README.md) (Russian) — sections, required translations, README rules.
- Planning (Russian): [TODO](../../TODO.md) · [ROADMAP](../../ROADMAP.md) · [archive](../archive/TODO_ARCHIVE.md) ·
  [AGENTS.md](../../AGENTS.md).
