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
2. **Release branch** from accepted main: stm32-gdbtest 0.1.0rc2, CHANGELOG 0.1.0-rc.2
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
| NUCLEO-F030R8, native ST-Link/SWD, OpenOCD, Windows | Single full run of 18 CMSIS cases; separate runner programming/identity/full-image/verify-only/timeout/recovery cycle | 5b7b466: CMSIS 18/18, lifecycle 10/10, restore PASS |
| Same Nucleo, HAL fixture | 17 cases, 6 positive repeats, timeout/recovery and restoration | 5b7b466: 17/17 + 6 repeats, timeout/recovery/restore PASS |
| WeAct BluePill-Plus F103C8, J-Link/SWD, Windows | Basic cases and runner lifecycle with recovery | 5b7b466: 10/10, restore PASS |
| BlackPill F411CE, ST-Link/SWD, OpenOCD and ST GDB Server, Windows | Basic cases and runner lifecycle with recovery for both backends | 5b7b466: OpenOCD 10/10; ST USB ERROR + reconnect, continuation PASS |
| Windows → Orange Pi 5 over SSH; pack/run --package; Hardware workflow | Repeat agreed remote matrix with packages of the same candidate | 5b7b466: Hardware 36788964902 PASS; 27 JSON verified |

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

stm32-gdbtest 0.1.0rc2, API_VERSION=1, specification 0.42. Windows docs/host 4/4 PASS.
Linux Docker: docs/format/host and nine CMSIS combinations passed (14 stages).
HAL initially failed CMake configuration because build/ci-gcc13 held a Windows cache;
it was preserved as ci-gcc13-windows-before-rc2. A separate clean HAL run passed
1/1: 19 CTest checks, 17 prepare cases and negative contracts. These are two runs,
not a single 15/15. Reports: build/rc2-offline-initial.json and build/rc2-offline-hal.json.
The published SHA still needs Docs/Offline. Candidate HW acceptance and consumer
integration remain open; release notes are a draft.

## rc.2 acceptance failure (2026-10-01)

Docs and all Offline jobs passed for e3f5233. Windows GDB → SSH/OpenOCD on Orange Pi,
NUCLEO-F030R8/ST-Link: 6 PASS, then HW_CI_TIM3_IRQ ERROR; stopped on first error.
TIM3_IRQHandler was reached, ICSR=32. Diagnostics confirmed xPSR: Bad register,
xpsr: available. Server: xPack OpenOCD 0.12.0+dev-02228-ge5888bda3-dirty.
GDB runs on Windows. Original HAL restored, HW_BOOT/HW_BLINK PASS, reset_run.
Evidence: build/rc2-acceptance/f030-full-20260930T221717Z/summary.json.

Fixed scenarios use SCB ICSR VECTACTIVE with CMSIS macro preflight. Firmware and
runtime are unchanged; the complete set and CI must be repeated on the new SHA.
Profile core_registers remains server-specific: diagnostic_errors preserves
unavailable xPSR. This diagnostic limitation does not mean no IRQ occurred.

Repeat at 8a7928c: 14 PASS, RTC_ALARM ERROR after reaching app_loop — SCB is outside the app.c DWARF context. HAL restore boot/blink PASS. The ICSR address and mask are now captured in RTC_IRQHandler before changing context (TECH-002). Evidence: build/rc2-acceptance/f030-full-20260930T222249Z/summary.json.

## CMSIS repeat on the corrected commit

Runtime/scenario SHA: a48158cbfc8c61e015f5e84daa494ce66f639ce0. One complete run:
18/18 PASS, followed by original HAL restoration: HW_BOOT/HW_BLINK PASS, reset_run.
Windows xPack GCC13/GDB, ST-Link/SWD, OpenOCD on Orange Pi over SSH.
ELF SHA256: 6a5ed3b0835ce5f093e808fcca6cce453399d1ad8d3e130816647c5d3afb8280.
Evidence: build/rc2-acceptance/f030-full-20260930T222540Z/summary.json.
The preceding 20260930T222451Z run stopped in the local report collector: concurrent
CTest prepare wrote additional result.json files to the same out directory.
HW_ADC_INIT was PASS; restore PASS. That run is not counted as a complete set;
the serial repeat used unchanged code. F030 offline 19/19, docs/host 4/4.
The newly published SHA still requires Docs/Offline. This SSH run does not
replace the separate local Windows/backend matrix.

## HAL F030 on the same candidate

At a48158c: 17/17 scenarios, six positive repeats after ADC injections, expected
timeout ERROR after entering loop, host recovery reset_run and ADC repeat PASS.
Original consumer HAL restored: HW_BOOT/HW_BLINK PASS, MCU running.
Same environment: Windows GCC13/GDB → SSH/Orange Pi/OpenOCD, NUCLEO-F030R8/ST-Link.
Evidence: tests/hal-f030/build/validation/20260930T222705.675442Z/summary.json.
HAL offline: 19/19. Pack/Hardware workflow, full-image/identity cycles and remaining
local/remote stands are not yet accepted. Scenario fixes require new CI; do not
tag or land yet. Subsequent documentation commits do not replace the stated
SHA of the scenarios actually executed.

## Runner lifecycle over SSH (2026-10-01)

Verified SHA: 873f1ac29f5c85b2049c10be773c8486a35c545c. Docs and all five
Offline jobs SUCCESS (Docs 36786189561, Offline 36786189557).
Windows GCC13/GDB, GDB servers on Orange Pi; SWD, no additional wiring.

| Stand | Steps | Restoration | Directory under build/rc2-acceptance |
| --- | --- | --- | --- |
| NUCLEO-F030R8 / ST-Link / OpenOCD | 10/10 | HAL boot/blink PASS, reset_run | f030r8-lifecycle-20260930T223538Z |
| WeAct BluePill-Plus F103C8 / J-Link | 10/10 | HAL boot/blink PASS, reset_run | f103c8-lifecycle-20260930T223631Z |
| BlackPill F411CE / ST-Link / OpenOCD | 10/10 | HAL boot/blink PASS, reset_run | f411ce-lifecycle-20260930T223716Z |

These are 10 validation steps, not 10 positive hardware scenarios:
build, prepare, boot, GPIO, strict identity, full-image A5, verify-only FF
(expected ERROR without writing), full-image FF, timeout (expected ERROR with
recovery), GPIO after recovery. Original consumer firmware was restored after
each set with boot/blink checks. Each step used the standard run_hw.py separately;
its summary/log/policy were saved before the next invocation, and CLI reports
remain in the profile build. The wrapper stops on the first unexpected outcome.

F030 pack also prepared 18 scenarios from the verified ELF. Linux package execution
and Hardware workflow are not yet confirmed. The runner home configuration for
F030 on Orange Pi still selects J-Link; the owner must switch it to native
ST-Link/OpenOCD before the workflow. The local remote.toml used the correct
ST-Link independently of that file. The local Windows/backend matrix, consumer
integration and final release notes remain pending.

## Hardware workflow: execution and lost reports

At 759840a: Hardware 36787681339, prepare/hardware SUCCESS. Packages built on GitHub Ubuntu, executed on Orange Pi Linux aarch64. Three summaries and the log report 10/10 each. However, open_package deleted earlier runs on each open: artifacts retain only one after-recovery JSON per board. These data support the execution log, not complete evidence retention; acceptance requires a repeat after the fix.

Local archive: build/rc2-acceptance/hardware-36787681339/hw; restore.json records boot/blink PASS for all three original HAL images, reset_run. The owner corrected the F030 runner stand to ST-Link/OpenOCD. Boards remain running. TC-133 covers the fix; Offline/Hardware must follow on the new SHA.

Local fix validation: Windows docs/host 4/4; Linux Docker host 1/1; 98 host tests (Windows: 8 platform skips). Two consecutive CLI prepare calls for one F030 package retained both JSON reports in separate sessions. Hardware repetition of the fix is pending.

## Acceptance at 5b7b466: packages and local stands (2026-10-01)

Code SHA: 5b7b4661a27db497f74f475de667b8df731e9c99. Docs 36788642783,
Offline 36788643033 and Hardware 36788964902 — SUCCESS. Hardware built packages
on GitHub Ubuntu and executed them on Orange Pi Linux aarch64: 10/10 steps each
for F030/OpenOCD, F103/J-Link, F411/OpenOCD. All 27 separate JSON reports were
checked against summary, including expected verify-only/timeout ERROR and recovery.
The owner-downloaded hardware-results.zip contains the same 27 JSON files byte for byte.
The initial Windows ZIP download network failure was not a workflow failure.
Local evidence: build/rc2-acceptance/hardware-36788964902, audit.json,
github-audit.json and restore.json. Original HAL restored, boot/blink PASS.

The owner moved all three stands to Windows without changing SWD wiring. Same SHA:

| Stand / set | Result | Evidence |
| --- | --- | --- |
| NUCLEO-F030R8 / ST-Link / OpenOCD, CMSIS | 18/18; restore boot/blink PASS | f030-windows-full-20260930T230819Z |
| Same Nucleo, lifecycle | 10/10; restore PASS | f030r8-windows-nucleo-f030r8-20260930T230946Z |
| Same Nucleo, HAL | 17/17, 6 repeats, expected timeout ERROR, recovery, ADC after recovery, restore PASS | 5b7b466: 17/17 + 6 repeats, timeout/recovery/restore PASS |
| WeAct BluePill-Plus / F103C8 / J-Link | 10/10; restore PASS | f103c8-windows-bluepill-jlink-20260930T231215Z |
| BlackPill / F411CE / ST-Link / OpenOCD | 10/10; restore PASS | f411ce-windows-blackpill-20260930T231302Z |
| Same F411, ST GDB Server 7.14 | 8 steps PASS, then USB ERROR before ready; after reconnect boot, timeout/recovery and after-recovery PASS, restore PASS | f411ce-windows-blackpill-stlink-20260930T231349Z and 20260930T231636Z |

Directories without a full prefix are under build/rc2-acceptance, each with summary.json.
ST server is not an uninterrupted 10/10: the original timeout never started, and
restoration through ST and OpenOCD also failed. ST reported Target USB comms error;
OpenOCD read invalid STLINK V8J0S0 / VID:PID 0000:0001 information. Manual USB
reconnect restored communication and HAL boot/blink. A subsequent boot prepared
the CMSIS image for the remaining two steps; original HAL was restored afterwards.
The cause is unknown; reconnect is not a runtime fix or evidence of long-run
stability. Keep this limitation visible in the release notes.

All three boards remain on Windows with original HAL running. Consumer integration,
final documentation/release text review and final SHA validation remain open.
Later documentation-only changes do not replace this hardware-tested code SHA.

## Consumer integration and publication gates

Consumer stm32-hwtest-blackpill: fb2d18626a3c9ff831bd8d2a0c58bb97c6150cbd,
pinning module 67b7431eabba970ed2f690fb5ac2fcec045cc06e (documentation-only changes
from hardware-tested 5b7b466). GitHub Offline
[36791792481](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill/actions/runs/36791792481)
— SUCCESS: five profiles, 120 CTest checks including 105 prepare checks.
Local Linux Docker: the same 120/120; Windows F411: 25/25 host/prepare.
F411/ST-Link/OpenOCD on Windows through the consumer CLI: 22/22 cases;
separate expected timeout ERROR with confirmed loop entry, host recovery,
then ADC DMA, boot and blink PASS. Original HAL firmware left running.
Consumer evidence: build/rc2-integration/linux-reports/summary.json,
windows-host.log, f411-20260930T232546Z/summary.json and recovery/summary.json.

Remaining gates: Docs and full Offline for the final documentation SHA, owner-approved
module land, consumer gitlink update and its new CI. The owner then lands the consumer
and publishes the signed tag/GitHub prerelease. No tag exists; release text is ready for review.

Publication completed: v0.1.0-rc.2 → a0d6547, signed tag Verified; GitHub
prerelease and tag text match docs/releases/v0.1.0-rc.2.md. Consumer main2b9d75f
pins this SHA, Offline36797076345 SUCCESS. Historical pending stages above
are complete; the tag remains immutable.
