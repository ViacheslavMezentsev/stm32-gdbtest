# stm32-gdbtest documentation

Documentation · [Русский](../ru/index.md)

[API specification 0.2.0](../TECHNICAL_SPECIFICATION_API.md) — rc.2 baseline and accepted first-extension requirements; separate Russian specification. Core remains rc.2: record/records and config/config_props are not integrated. [Status and migration](../research/api-extension/en/m5-contract.md).

[API extension research](../research/api-extension/en/index.md) — record/read/frames/context/finish using existing scenarios, plan and results.

[Research 2: adaptive scenario tree](../research/adaptive-test-tree/en/index.md) — simulated engine, JSON oracle and HTML player.

[GDB Python research for rc3](../research/rc3-gdb-python/en/index.md): plan, separate R1–R18 reports and results.

- [API evolution and specification boundaries](../research/rc3-gdb-python/en/api-evolution.md) — draft conventions, verification criteria and transition order.
- [API scope proposal](../research/rc3-gdb-python/en/api-proposal.md) — operations, contracts, implementation packages and open questions.
- [R1–R18 summary](../research/rc3-gdb-python/en/summary.md) — all reports, findings and evidence boundaries.
- [API, techniques and patterns](../research/rc3-gdb-python/en/scenario-tools.md) — application areas, classification and API properties.
- [Named execution context](../research/rc3-gdb-python/en/execution-context.md) — snapshot contract proposal.
- [Technical debt](../research/rc3-gdb-python/en/technical-debt.md) — paused stages and open limitations.

[F429 RTC/Sleep/deadline/recovery:20/20 HW +5 repeats, external timeout/recovery and HAL restore PASS; specification0.57.](F429_CMSIS_RTC_SLEEP.md)

[F429 ADC/DMA/units/failures:15/15 HW +3 repeats, HAL restored; specification0.56.](F429_CMSIS_ADC_DMA.md)

[F429 CMSIS baseline:7/7 HW, HAL restored; specification0.55. Fifth CI profile; ADC/RTC remain pending.](F429_CMSIS_BASELINE.md)

[F401 RTC/Sleep/deadline/recovery:20/20 HW +5 repeats, external timeout/recovery and HAL restore PASS; specification0.54.](F401_CMSIS_RTC_SLEEP.md)

[F401 ADC/DMA/units/failures:15/15 HW and three positive repeats, HAL restored; specification0.53.](F401_CMSIS_ADC_DMA.md)

[F401 CMSIS baseline: 7/7 HW through ST-Link/OpenOCD, HAL boot/blink restored. Flash256/RAM64; ADC/RTC are not migrated yet.](F401_CMSIS_BASELINE.md)

[Hardware metrics and results table](HARDWARE_METRICS.md).

[rc.2 readiness and acceptance matrix](RC2_READINESS.md).

[HAL F030 hardware acceptance](F030_HAL_VALIDATION.md): 17/17, six repeats, timeout/recovery and original firmware restoration verified on Windows/ST-Link/OpenOCD; specification 0.40. API unchanged.

Introduction — [README](../../README.en.md): an implementation of [DDTT](DDTT.md) for
STM32 — checks of running firmware on a real board through GDB and an SWD debugger,
written as scenarios in the project repository. Requirements —
the [specification](../TECHNICAL_SPECIFICATION.md) (kept in Russian only).

## Getting started

- [DDTT specification](DDTT.md) — the debugger-driven testing on target method: terms, principles, requirements for scenarios, stands and tools.

- [Getting started](GETTING_STARTED.md) — requirements, checks without a board, submodule integration.
- [Writing tests](TEST_AUTHORING.md) — the process for people and AI agents.
- [API, CLI and migration](API.md) — CMake, the `case` decorator, Target API, `run`, migrating from hwtest.

## Mechanisms

- [ELF/HAL contracts](CONTRACTS.md) — offline checks of functions, types, enums and source hashes.
- [HAL macros](HAL_MACRO_GUIDE.md) — choosing macros, context and the macro contract.
- [Images and CRC](IMAGES.md) — ELF sections, BIN, full image and CRC-32/ISO-HDLC.
- [Manifest](MANIFESTS.md) — runtime and build provenance metadata.
- [GDB servers](BACKENDS.md) — OpenOCD, ST-LINK GDB Server, J-Link; the stand.
- [Identity and Flash](TARGET_IDENTITY.md) — DEV_ID and the factory Flash size.
- [Debugger ownership](DEBUGGER_OWNERSHIP.md) — cross-project locking on Windows and Linux.
- [Linux stand](LINUX_STAND.md) — environment without root (Ubuntu 20.04, Orange Pi 5), USB, J-Link, remote GDB server over SSH, WSL2.
- [Hardware CI](HARDWARE_CI.md) — prepared run packages, a self-hosted runner on Orange Pi, 24/7 runs.

## Status and maintenance

- [F030 CMSIS baseline](F030_CMSIS_BASELINE.md) — four hardware scenarios and limitations.

- [CMSIS example migration](CMSIS_MIGRATION.md) — baseline, F030 gaps and acceptance.

- [Status](STATUS.md) — verified scope, stands and limits.
- [Checks and CI](testing.md) — CI levels, Docker image, hardware check of the CI firmware.
- [Versions and releases](VERSIONING.md) — SemVer, tags, release preparation.
- [Maintenance](maintenance.md) — workflow, branches, commits, bilingual documentation.
- [HOWTO](HOWTO.md) — git commands (including `git land`), common stand, debugger and Docker problems, undoing changes.
- [CHANGELOG](../../CHANGELOG.en.md), [roadmap](../../TODO.md) (Russian), [AGENTS.md](../../AGENTS.md).

[F030 CMSIS: TIM3/IRQ](F030_CMSIS_TIMER.md).

F030 ADC/DMA: raw samples and timeout, core API unchanged. [ADC/DMA](F030_CMSIS_ADC_DMA.md).

F030 ADC conversion and numeric scenarios; core API unchanged. [ADC units](F030_CMSIS_ADC_UNITS.md).

F030 Sleep/WFI: profile scenarios using GDB unwind; core API unchanged. [Sleep evidence](F030_CMSIS_SLEEP.md).

F030 RTC: LSI Alarm A, 16/16 HW PASS, HAL restored. Core API unchanged. [RTC](F030_CMSIS_RTC.md).

F030 busy ADC check; API unchanged. [Report](F030_ADC_BUSY.md).

F030 RTC deadline through argument injection; API unchanged. [Report](F030_RTC_DEADLINE.md).

[F030 HAL→CMSIS mapping and branch batch order](F030_CMSIS_ACCEPTANCE.md).

- [F030 HAL regression: migration plan and acceptance](F030_HAL_REGRESSION.md).

[Techniques catalogue TECH-001…008](TESTING_TECHNIQUES.md) — stable scenario references, build prerequisites, limits and restoration. Preserve TECH-001/003/004 references when migrating HAL scenarios.

[Standalone F030 HAL regression](F030_HAL_REGRESSION.md): test consumer, no API changes.

- [F103 CMSIS: clocks/GPIO/SysTick/TIM2](F103_CMSIS_BASELINE.md).

- [F103 CMSIS: ADC/DMA/units/failures](F103_CMSIS_ADC_DMA.md).

- [F103 CMSIS: RTC/Sleep/deadlines/recovery](F103_CMSIS_RTC_SLEEP.md).

- [F411 CMSIS: clocks/GPIO/SysTick/TIM2](F411_CMSIS_BASELINE.md).

- [F411 CMSIS: ADC/DMA/units/failures](F411_CMSIS_ADC_DMA.md).

- [F411 CMSIS: RTC/Sleep/deadlines/recovery](F411_CMSIS_RTC_SLEEP.md).

[Five-profile acceptance review and remaining HAL checks](CMSIS_ACCEPTANCE.md).

[HAL F030: five GPIO/RCC techniques and source variants](F030_HAL_GPIO_RCC.md).
