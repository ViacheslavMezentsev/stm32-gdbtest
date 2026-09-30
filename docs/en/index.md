# stm32-gdbtest documentation

Documentation · [Русский](../ru/index.md)

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
