# stm32-gdbtest documentation

Documentation · [Русский](../ru/index.md)

Introduction and purpose of the module — [README](../../README.en.md). Requirements —
the [specification](../TECHNICAL_SPECIFICATION.md) (kept in Russian only).

## Getting started

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
- [Debugger ownership](DEBUGGER_OWNERSHIP.md) — cross-project locking on Windows.

## Status and maintenance

- [Status](STATUS.md) — verified scope, stands and limits.
- [Checks and CI](testing.md) — CI levels, Docker image, hardware check of the CI firmware.
- [Versions and releases](VERSIONING.md) — SemVer, tags, release preparation.
- [Maintenance](maintenance.md) — workflow, branches, commits, bilingual documentation.
- [CHANGELOG](../../CHANGELOG.en.md), [roadmap](../../TODO.md) (Russian), [AGENTS.md](../../AGENTS.md).
