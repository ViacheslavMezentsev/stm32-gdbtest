# Changelog

All notable changes to this project are documented in this file ([Русский](CHANGELOG.md)).
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions: [policy](docs/en/VERSIONING.md).

## [Unreleased]

### Added

- `stm32_gdbtest_attach(... PROFILE <target.toml>)`: the MCU description as a separate file,
  shared `Tests` (scenarios, requirements, contracts) for several MCU variants of one firmware.
- Prepared run packages: `pack` prepares scenarios without hardware and writes a zip with the
  ELF, build manifest, profile, scenarios and file SHA-256; `run --package` verifies the package
  and runs it on a stand without rebuilding; `run_hw.py --package`.
- The Hardware workflow (manual only): build and `pack` on GitHub, run the packages on a
  self-hosted runner with a stand. `run_hw.py --repeat` for loop runs with `soak.json`.
  Checked: packages from Windows on Orange Pi 5 — three stands × 10/10; a loop with interruption;
  the Hardware workflow on the Orange Pi 5 runner service — three stands × 10/10.
  Documentation `docs/ru|en/HARDWARE_CI.md`.
- DDTT 0.2 method specification (Debugger-Driven Testing on Target) `docs/ru|en/DDTT.md`:
  scope, terms, principles, model, requirements for scenarios, stands, tools and agents
  per RFC 2119; stm32-gdbtest is the reference implementation.
- Remote GDB server: the `[remote]` stand table. The runner and GDB run on Windows or in
  WSL, the server and the debugger on a Linux stand host (Orange Pi 5); one SSH session
  with port forwarding and a helper script, the stand host's lock, the server stopped
  when the session closes or breaks, SSH keys only; `doctor` checks the stand host.
  Template `Tests/firmware/stands/remote.example.toml`. Checked from Windows to Orange Pi 5:
  F411CE/OpenOCD, F103C8/J-Link CE, F030R8/J-Link STLink — 10/10 each.
- `doctor` finds GDB in `ARM_TOOLCHAIN_ROOT` and in the default xPack directory on Windows,
  like `run_hw.py`.
- HOWTO `docs/ru|en/HOWTO.md`: git commands and the `git land` alias (fast-forward merge
  without pull requests plus branch deletion), undoing changes, common Linux stand,
  debugger and Docker problems; linked from AGENTS.md.
- Stand setting `startup_timeout_s` (1…120 s, default 10) — how long to wait for the
  GDB server to become ready; the timeout message names the limit and the setting.
- Hardware runs on Linux x86_64 and aarch64 (glibc ≥ 2.31, including Ubuntu 20.04 on
  Orange Pi 5): debugger lock with `flock` in a host-wide directory
  (`STM32_GDBTEST_LOCK_DIR`, default `/tmp/stm32-gdbtest-locks`) with abandoned-ownership detection, the
  server and GDB in their own process group stopped with `SIGTERM`/`SIGKILL`, Linux
  server names without `.exe`. Checked on Orange Pi 5: F411CE/OpenOCD, F103C8/J-Link CE, F030R8/J-Link STLink — 10/10 each.
- `tools/linux_stand.py`: stand environment without root — Python 3.11
  (python-build-standalone), CMake 3.28.3, Ninja 1.12.1, xPack GCC 13.3.1-1.1, xPack
  OpenOCD 0.12.0-7 and CMSIS from `tools/linux-stand.lock.json` with SHA-256 for x86_64
  and aarch64; `env.sh`.
- `doctor` command: GDB-Python, binutils, CMake, Ninja, the lock directory, the stand,
  OpenOCD `interface/stlink.cfg` and on Linux ST-Link and J-Link devices on USB with
  access rights.
- CI: the `linux-stand` job in an `ubuntu:20.04` container on x86_64 and aarch64 —
  environment installation, host tests, `doctor`, build and preparation of the CI firmware.
- Linux stand documentation `docs/ru|en/LINUX_STAND.md`; specification revision 0.7.
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

- The `linux-stand` CI job uses the `ubuntu:20.04` container pinned by digest.
- Project definition: a verification loop for STM32 firmware on real hardware for
  agent-driven and manual development, technically a debugger-driven test framework.
  README, documentation maps, stand layouts in STATUS, layout choice in getting
  started, the agent loop in test authoring; specification revision 0.10.
- `run_hw.py` works on Linux (toolchain and Cube from `env.sh`) and records the host OS
  and architecture in `summary.json`.
- Documentation moved to `docs/ru/` with English versions in `docs/en/`, `index.md`
  documentation maps and navigation lines; README.en.md added. Pages were checked
  against the current features: preparation without hardware, Linux for the offline
  part, full image through ST-LINK GDB Server, macro context in the compilation unit,
  the F030 Flash size address, verified stands; specification revisions 0.5 and 0.6.
- Build, build manifest, offline contracts and image preparation also work on Linux:
  compiler commands are split by shell rules, binutils names follow the GDB suffix.
  (hardware runs on Linux — see Added).
- AGENTS.md is a short rule list; branches `<agent>/<task>`, merging without pull
  requests, signed Conventional Commits; specification revision 0.3.
- Gaps of the derived BIN are filled with 0xFF. This does not guarantee filled holes
  when the original ELF is loaded; the policy and the full-image CRC plan — docs/IMAGES.md.
- README reworked as a user introduction: purpose, approach, contents, dependencies
  and navigation. The check and limitation snapshot moved to docs/STATUS.md; a Mermaid
  diagram was added.

### Fixed

- `reach` compares the frame name without `[clone …]` suffixes, `const` and parameters: with
  LTO GDB names the frame by its ELF symbol (`HmiManager::init() [clone .constprop.0]`), and
  a correct stop gave FAIL.
- A build manifest with empty `cube_packages` and `library_versions` is no longer
  rejected: HAL and CMSIS may come from outside an `STM32Cube_FW_*` package (Arduino Core STM32).
- Remote server: the runner sends a heartbeat into the SSH session every 2 s; when the link
  is lost without closing the connection (Wi-Fi, cable, sleep), the server on the stand
  host stops and the debugger is freed after 15 s instead of hours. Checked on Orange Pi 5
  by pulling the cable.
- `tools/linux_stand.py` retries downloads and `git fetch` on transient server errors
  (up to 4 attempts with pauses); CI jobs cache the pinned downloads.
- `tools/linux_stand.py install --only …` verifies the selected components only: the
  `prepare` job of hardware CI no longer fails on the absent OpenOCD.
- The BIN is built only from the selected load sections (`objcopy -j`): an empty section
  with a RAM address (for example an empty `.data`) no longer stretches it to hundreds of
  MiB before the "BIN extent differs" refusal. Host test and a CI regression on a real ELF.
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
