# Preparing stm32-gdbtest 0.1.0-rc.2

[Documentation](index.md) → rc.2 readiness · [Русский](../ru/RC2_READINESS.md)

Agreed candidate scope, 2026-10-01. Base main `7f3c65b`; this is an acceptance plan,
not a claim that rc.2 is released. The documentation audit is in main `eaf31ea`; release branch
`codex/release-0.1.0-rc.2` reports `0.1.0rc2`. The tag is not published yet.

## Included scope

- Post-rc.1 fixes: CMake 3.25 manifest, HAL macro preflight for C++ and missing
  DWARF types, J-Link mapping for STM32F103CBT6.
- CMSIS F030: 18 cases, timer/IRQ, ADC/DMA, numeric vectors, RTC, Sleep/WFI
  and selected failure paths.
- Separate tests/hal-f030: 17 original HAL application cases, provenance/licenses,
  build/prepare and negative contracts in CI; repeatable HW acceptance with restoration.
- TECH-001…008 catalogue, lowercase tests with legacy Tests compatibility,
  local remote.toml files and clarified instructions.

F103/F411 in tests/firmware retain two basic boot/GPIO cases each.
examples/minimal-consumer remains the F411 integration example. Full peripheral
migration for F103/F411/F401/F429, RISC-V, QEMU/Renode, external instruments,
multicore, a Python package and CI optimisation are outside required rc.2 scope.
API_VERSION=1 and schemas remain unchanged unless the audit identifies a required
contract change; that would need a separate decision and migration guidance.

## Sequence and gates

1. **Documentation review**, codex/rc2-docs-audit: current guides and plans match
   code, dates and evidence are separated from history, RU/EN agree. Do not change
   the version or edit the published rc.1 tag description.
2. **Release branch** from accepted main: Python 0.1.0rc2, CHANGELOG 0.1.0-rc.2
   in both languages, release specification revision, README/API/STATUS and
   docs/releases/v0.1.0-rc.2.md. Notes remain an explicit draft until acceptance.
3. **Offline** at the published SHA: Docs and all five Offline jobs; nine CMSIS
   MCU/GCC combinations, GCC13 HAL, host/format/contracts and artifacts.
4. **Hardware acceptance** of the candidate using the table below. Preserve the
   first unexpected result; a fix creates a new SHA and requires affected checks again.
5. **Consumer**: pin the candidate via an actual gitlink, repeat build/prepare and
   agreed HW/recovery checks; publish consumer changes separately.
6. **Publication**: verify final SHA, CI, protocols and notes; the owner lands,
   then creates signed annotated tag v0.1.0-rc.2 and a GitHub prerelease.
   Do not execute tag publication commands before the final review.

| Stand / mode | Required rc.2 evidence | Status |
| --- | --- | --- |
| NUCLEO-F030R8, native ST-Link/SWD, OpenOCD, Windows | Single full run of 18 CMSIS cases; separate runner programming/identity/full-image/verify-only/timeout/recovery cycle | Awaiting candidate |
| Same Nucleo, HAL fixture | 17 cases, 6 positive repeats, timeout/recovery and restoration | Awaiting candidate; prior acceptance in F030_HAL_VALIDATION |
| WeAct BluePill-Plus F103C8, J-Link/SWD, Windows | Basic cases and runner lifecycle with recovery | Awaiting candidate |
| BlackPill F411CE, ST-Link/SWD, OpenOCD and ST GDB Server, Windows | Basic cases and runner lifecycle with recovery for both backends | Awaiting candidate |
| Windows → Orange Pi 5 over SSH; pack/run --package; Hardware workflow | Repeat agreed remote matrix with packages of the same candidate | Orange Pi SSH available, runner active; confirm board connections |

tests/firmware/run_hw.py checks the runner lifecycle through boot/GPIO.
It does not automatically run all 18 F030 cases: execute the full suite separately
through normal CLI/CTest with an explicit stand and external timeout.
Hardware commands write Flash. Identify the stand before each suite;
afterwards restore agreed firmware and confirm reset_run.

Do not substitute old PASS for an unavailable Linux stand: record the limitation
and agree a reduced rc.2 matrix before publishing. Historical results are not new
checks; do not claim additional boards were tested.

## Documentation review

Scope is all tracked module Markdown files, including RU/EN, examples, requirements,
licenses and prior release notes. Structural checks cover link files and language
pairs; they do not establish the meaning of every external URL, anchor or command
on hardware that is not connected.

| Group | Source of truth / action |
| --- | --- |
| README, index, STATUS, TODO, CHANGELOG | main contents and CI/HW evidence; remove completed future work from current status |
| API, GETTING_STARTED, TEST_AUTHORING, CONTRACTS, HAL_MACRO_GUIDE | CLI help, CMake attach, Target API, contracts and actual tests directories; preserve Tests compatibility |
| testing, HARDWARE_CI, LINUX_STAND, HOWTO, maintenance | workflows, run_checks, run_hw and stand tools; distinguish offline, HW and stand availability |
| BACKENDS, DEBUGGER_OWNERSHIP, TARGET_IDENTITY, IMAGES, MANIFESTS | Backend/lock/image/manifest implementation and host checks; do not infer unsupported features |
| CMSIS_MIGRATION, TESTING_TECHNIQUES, F030 protocols | Current scenario inventory and dated reports; history remains historical |
| VERSIONING, specification, releases | __init__ version, agreed gates and evidenced SHA; published rc.1 notes unchanged |
| SOURCE, licenses, example README and requirements | Provenance, retained licenses and actual commands/IDs; no test hooks |

## Tag and Releases text

Canonical text is docs/releases/v0.1.0-rc.2.md, Russian then English, using
[VERSIONING](VERSIONING.md). The same file supplies the signed tag message
(--cleanup=verbatim) and the GitHub prerelease description. Distinguish additions,
fixes, migration and limits; include Python/API/specification versions and links
to the verified matrix.

Never prefill PASS, substitute a later documentation SHA for a runtime SHA, or try
to embed a commit's own SHA inside that commit. Record the hardware-tested code SHA
in the protocol; obtain the final tag SHA from Git when checking publication.
For a subsequent text-only change explicitly verify no code/firmware changed and
repeat documentation/CI checks at the new SHA. Code, profile, toolchain or scenario
changes require the affected HW acceptance again. Never move a published tag;
resolve any discrepancy before publication.

## Environment precheck (not rc.2 HW acceptance)

2026-10-01: the owner confirmed three stands on Orange Pi. Doctor over SSH
for F030/ST-Link/OpenOCD, F103/J-Link and F411/ST-Link/OpenOCD completed without
FAIL/WARN: tools, USB serials and access permissions match the configurations.
Runner.Listener is active; the Hardware workflow itself has not been run yet.
No GDB servers or MCU connections were started and no Flash was written.
Local reports: build/rc2-readiness/*-doctor.json; *-remote.toml files are gitignored.

Documentation checks: 86 Markdown files, 57 internal anchor links — no errors;
docs/spec/links/pairs on Windows and Linux Docker — 3/3 on each OS.
Code, firmware and published rc.1 notes are unchanged. Specification revision is
0.41; final TC-132 acceptance and the release specification revision remain pending.

## Local release-branch preparation (2026-10-01)

Python 0.1.0rc2, API_VERSION=1, specification 0.42. Windows docs/host 4/4 PASS.
Linux Docker: docs/format/host and nine CMSIS combinations passed (14 stages).
HAL initially failed CMake configuration because build/ci-gcc13 held a Windows cache;
it was preserved as ci-gcc13-windows-before-rc2. A separate clean HAL run passed
1/1: 19 CTest checks, 17 prepare cases and negative contracts. These are two runs,
not a single 15/15. Reports: build/rc2-offline-initial.json and build/rc2-offline-hal.json.
The published SHA still needs Docs/Offline. Candidate HW acceptance and consumer
integration remain open; release notes are a draft.
