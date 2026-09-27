# Changelog

All notable changes to this project are documented in this file ([Русский](CHANGELOG.md)).
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions: [policy](docs/VERSIONING.md) (Russian).

## [Unreleased]

### Added

- Hardware check of the CI firmware `Tests/firmware/run_hw.py` (10 steps: programming,
  repeat, strict identity, full image, verify-only, timeout/recovery); at commit `fbc103d`
  F030R8/J-Link STLink, F103C8/J-Link, F411CE/OpenOCD and F411CE/ST-LINK GDB Server passed.
- `.clang-format` — C/C++ source style; CI format level (`clang-format --dry-run --Werror`).
- `run --prepare-only`: every step before the GDB server (stand if selected, profile,
  ELF snapshot, build manifest, requested contracts, sections and image, including
  full mode) without debugger locking, server or connection; report with `mode: prepare`.
  CMake registers `prepare.<ID>` tests labelled host and prepare.
- GitHub Actions CI: the Docs workflow (specification `check_spec.py --strict`, links,
  RU/EN pairs) and Offline (host tests on Windows and Linux, CI firmware build,
  manifest, `prepare`, full image and 10 negative ELF contracts) without a debugger or board.
- CI Docker image `ci/docker` from the pinned `ci/dependencies.lock.json`: Ubuntu 24.04,
  xPack GCC 13.3.1/14.2.1/15.2.1 with GDB-Python, CMake 3.28.3, Ninja 1.12.1, CMSIS of
  STM32CubeF0/F1/F4; `ci/run_checks.py` runs locally and on GitHub.
- CI firmware `Tests/firmware` on CMSIS without HAL or stm32-cmake-yml: profiles F030R8
  (Cortex-M0), F103C8 (Cortex-M3), F411CE (Cortex-M4) with scenarios and contracts.
- Bilingual maintenance rules `docs/ru|en/maintenance.md`, check description
  `docs/ru|en/testing.md`, English changelog.
- J-Link mapping STM32F030R8T6 → STM32F030R8: Nucleo/J-Link STLink/SWD, 17 consumer
  scenarios, Flash/readback and reset/run verified; host65.
- Optional --image-policy / STM32_GDBTEST_IMAGE_POLICY: full BIN with an explicit
  range/fill, transport ELF for GDB, comparison of all bytes and CRC-32/ISO-HDLC of the
  readback on the host. Verify-only detects a wrong tail without programming.
- 12 host regressions; full-image mode verified on F411/OpenOCD and F103/J-Link with
  an A5/FF tail, the expected ERROR, recovery and HAL macros after load.
- API, ELF/HAL contracts, HAL macros, manifest, backend, identity and debugger
  ownership guides moved here and updated; stand evidence is linked.
- Initial snapshot of the validated stm32_gdbtest prototype from stm32-hwtest-blackpill.
- Runner/GDB-Python, CMake/CTest, HAL/ELF contracts, JSON/JUnit, three backends,
  cross-project Windows mutex and an independent consumer example.
- Host tests with separate fixtures and instructions for people and AI agents.

### Changed

- Build, build manifest, offline contracts and image preparation also work on Linux:
  compiler commands are split by shell rules, binutils names follow the GDB suffix.
  Hardware runs remain Windows-only; the refusal on another OS comes after stand and
  profile selection, before debugger locking.
- AGENTS.md is a short rule list; branches `<agent>/<task>`, merging without pull
  requests, signed Conventional Commits; specification revision 0.3.
- Gaps of the derived BIN are filled with 0xFF. This does not guarantee filled holes
  when the original ELF is loaded; the policy and the full-image CRC plan — docs/IMAGES.md.
- README reworked as a user introduction: purpose, approach, contents, dependencies
  and navigation. The check and limitation snapshot moved to docs/STATUS.md; a Mermaid
  diagram was added.

### Fixed

- CI firmware and minimal consumer linker scripts: the `.data` load address is
  4-byte aligned (the unaligned copy caused a HardFault on Cortex-M0); CI rejects
  unaligned load sections. The F103C8 CI profile uses the PB2 LED (WeAct BluePill-Plus).
- docs/STATUS.md: the host test count and the F030R8 J-Link mapping match the code.
- Flash is compared by loadable ELF sections/LMA: differences in non-loaded gaps no
  longer cause a false error or reprogramming.
- Bounds/overlap validation before the server, block readback, explicit evidence scope.

No release or tag has been created yet; the separate Git history and submodule
integration are already verified. Historical hardware results do not replace a check
of the new integration.
