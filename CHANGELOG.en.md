# Changelog

All notable changes to this project are documented in this file ([Русский](CHANGELOG.md)).
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions: [policy](docs/en/VERSIONING.md).

## [Unreleased]

- Added RU/EN API reference cards with examples and support versions. Specification 0.67/API 0.2.4 fixes the erroneous force_return description without code changes.

- Specification 0.66 clarifies L0/L6 procedures; adds a practical guide to Docker volumes, snapshots, failure evidence and stand restoration. Runtime/API unchanged.

## [0.3.0-rc.1] - 2026-10-05

Extended scenario API; the release is being prepared and the tag is published by the owner.

### Added

- Navigation and observation: `reach` with a condition, `resume`, `step`, `until`, `finish`, `Point` with `with` and `remove()`, and `watch` on writes to an addressable object.
- Invocation and control: `ret` with a typed value, `call` of firmware functions, `reset` with a command from `api.toml`, and `execute` of debugger commands with a journal.
- Reading and evaluation: `read`/`write` of objects, `evaluate` of expressions with a type conversion, `registers` of a frame, and `frames` with a walk limit.
- Run profile: `profile` reads `target.toml` as before and provides the sections `target`, `api`, `user`, `image`,
  `data`, `files`, `build`, `case`, `stand`, `gdb`, plus `get("a.b")`, `origin(path)` and `snapshot()`;
  `t.record(name, t.profile)` records a snapshot. API specification 0.3.4.
- Project data files: a `[data]` table in `session.toml` (`board = "board.toml"`) gives `t.profile.data["board"]`; the
  file is captured with the configuration and carried in packages. The fixture profiles gained a `board.toml`.
- Build facts: `t.profile.build` lists the compiler, Cube packages, CMSIS/HAL versions from macros and the `-D` keys;
  they show whether the firmware uses HAL (`USE_HAL_DRIVER`) or LL.
- One `check` for every check: the matchers `within`, `near`, `one_of` keep the value and the bounds in the report,
  `check(name, actual)` tests truth, `check(rows)` checks a table of rows with GDB expressions.
- Firmware strings: `evaluate(path, as_type=str)` reads a C string from a `char` array or a `char *` pointer, the matcher
  `matches(pattern)` checks it with a Python regular expression. The GDB functions `$_streq`, `$_strlen`, `$_memeq`,
  `$_regex` work right in a `check(rows)` table; the table rules are described on the `check` card. The `HW_CI_STRINGS`
  scenario and the `app_info` strings of the fixture firmware. API specification 0.3.5.
- Symbols and memory: `symbol(name)` gives the address, size, type and section; `memory(address, size)` reads SRAM or
  the profile flash, `memory(address, data)` writes bytes into SRAM with verification; peripheral addresses are refused.
- Frame variables: `locals()` and `arguments()` as one dictionary, optimized-out values listed separately.
- Point control: `Point.enable()`/`disable()` keep the counter, `condition` is writable; the `breakpoint_limit` budget
  counts active points only.
- Shared scenario directory: `tests/firmware/common/tests` for every profile; a user project adds search directories
  with `TEST_DIRS` in CMake or a repeated `--tests` in the CLI, and the package carries them along.
- Nine showcase scenarios: `HW_CI_INJECT_ZERO`, `HW_CI_WHO_WRITES`, `HW_CI_RETURN_VALUE`, `HW_CI_CONDITIONAL_STOP`,
  `HW_CI_STEP_SOURCE`, `HW_CI_UNTIL_TARGET`, `HW_CI_POINT_BUDGET`, `HW_CI_PROFILE`, `HW_CI_CALL_PREDICATE`.
- The fixture scenarios keep the original `@case` name: a test case reads clearer that way
  inside a script. The `@test` alias remains and is covered by `HW_CI_TEST_ALIAS`.
- The `@test` decorator as an alias of `@case`; the static collector accepts both names.
- `api.toml` keys: `frames.limit`, `call.depth`, `call.args_max`, `execute.output_limit_chars`,
  `reset.command`, `app.delay_ms`.

### Changed

- The module version is raised to `0.3.0`; `API_VERSION=1` and the JSON/TOML schemas are unchanged.
- The API reference is grouped into methods, properties, decorators, classes and errors; the `read` and `evaluate` rows render correctly again.
- A stop is classified by the kind of the reported point, not only by the debugger reason.
- The `config`, `config_props`, `settings` and `sources` properties are removed without aliases: `profile` replaces
  them (`target.config['api']['user']` → `target.profile.user`). They were not part of any published tag.
- Scenarios shared by the profiles moved from the profile directories into the shared directory; `HW_CI_SETTINGS` is
  replaced by `HW_CI_PROFILE`.
- `value`, `fields`, `set_value` and `force_return` are deprecated: the first call in a run adds a `deprecated` warning
  with the replacement to the report; removal in 0.4.0. `@case` stays the primary name without a warning.
- Scenarios and examples follow the 0.3.0 conventions: the Target object is `t` everywhere, expectations that follow
  from the device are firmware identifiers (`'DMA_CCR_MINC | DMA_CCR_PSIZE_0 | …'` instead of `1418`, `TIM2_IRQn + 16`
  instead of `44`), physical quantities are named constants; the replacements were compared with the numbers on the ELF.
- The order-preservation test of the former `_check_values` helper is removed together with the helper.
- `HW_CI_MEASUREMENT_SERIES` no longer requires distinct temperature values: the temperature may stay put for the series.
- An evaluation error of a string cell of `check(rows)` names the row, the cell and the rule: a table string is a GDB expression.

### Fixed

- `read` and `evaluate` of a pointer return the address it holds, not the address of the pointer itself: HAL checks
  such as `hadc.Instance == ADC1` compare the right values again.
- `Point.addresses` returns integer addresses instead of `gdb.BreakpointLocation` objects; a value that cannot be
  written as JSON no longer costs the run its report: the agent keeps it as its `repr`.
- Navigation follows the GDB version: the reference is GDB 15.2 (xPack 14.2.1). On GDB 14 a stop event has no
  reason, so the kind is derived from the command, the address and the frame, marked `inferred` and warned once
  (`inferred_stop`); an inserted watch reason is no longer presented as native. API specification 0.3.2.
- `finish` returns the value from the GDB value history (it was always `unavailable`), `returned_from` and a `void`
  state; `until(location)` reports `reached` only at the target address, otherwise `frame_exited`.
- `breakpoint`/`reach` accept `when=` again as the former name of `condition`, `temporary` of `breakpoint` is positional again,
  `Point` keeps `is_valid()`/`delete()`: 0.1/0.2 scenarios run unchanged. API specification 0.3.1.
- A repeated point with another condition, or a temporary one, is no longer replaced by the existing point, and `reach` no
  longer deletes a scenario point at the same place; `clear()` removes every point, not every second one.
- `write` passes a `bool` as 1/0, refuses values without a GDB literal (`unsupported_value`) and verifies an expression
  (an enum constant) by its result; `ret` takes signedness from `Type.is_signed` (for example `size_t`).

### Limitations

- Pointers, objects wider than eight bytes and floating-point values cannot be watched.
- Some combinations deliver no stop event for a watch point: the stop is marked `inferred` and confirmed by the changed object.
- `finish()` does not publish the staged stack copy.
- Hardware verification covered five stands; native DAP stands were not used.
- New methods and showcase scenarios are covered by host tests; the run on the five stands is still pending.
- The fault-handler points the agent sets at boot take slots of `breakpoint_limit`.

## [0.2.0-rc.1] - 2026-10-03

- Local research and prototypes are excluded from the published tree while retained in the developer workspace. Accepted results are documented separately; docs.public checks files and links against .gitignore filters. Main specification 0.65 defines L0–L6; API specification 0.2.3 clarifies public criteria without method changes.

Candidate agreed; local preparation, not published. [Acceptance and migration](docs/en/RC020_READINESS.md).

- Standardized the teaching style of 35 production scenario/helper files: RU/EN headers, English explanations, 120-character lines and no optional trailing commas. Executable ASTs match the previous revision.

- Migrated production scenarios: 44 table blocks / 282 checks; session.toml and VDDA/temperature series on five CMSIS profiles. HW 103/103 CMSIS, 22/22 HAL F030, 1/1 minimal consumer; separate recovery/restoration checks. Main specification 0.63; API 0.2.2 unchanged. [accepted results](docs/en/API_ACCEPTANCE.md).

- Integrated the first package: record/records, public RecordError, config/config_props, explicit SESSION_CONFIG and TOML snapshot transport to GDB/packages. Legacy mode retained. Development version 0.2.0.dev0, API_VERSION=1; API spec 0.2.2, system spec 0.62. Paired scenarios checked on F030/F103/F411; release remains separate.

- Documented the accepted first extension: API spec 0.2.0 and system spec 0.60, record/records, errors and session.toml configuration. Module target 0.2.0, API_VERSION=1; integration not authorized, numeric bounds open. Core behavior unchanged.

- Combined both studies for main: GDB Python/API reports and the simulated adaptive tree with its workflow player. Experimental tools remain isolated; API agreement and hardware technical debt remain open.

- Concluded the current R1–R18 research cycle with open technical debt. Added RU/EN draft API evolution conventions, system/API specification boundaries, operation contract cards and outcome verification. Normative specifications and core unchanged; HW remains paused.

- rc3 API draft: added frame group (frames/frame/arguments/locals), exact-depth caller helper and nearest-ancestor search. Defined incomplete-stack and reference freshness boundaries, distinguished backtrace from call history, and recorded graphs as separate debt. RU/EN documentation only.

- rc3 research: separate RU/EN API scope draft based on R1–R18 — observation, navigation and intervention packages, provisional signatures/result models, compatibility and owner decision questions. Implementation and HW remain paused.

- rc3 research: summary of separate R1–R18 reports, API/technique/pattern classification, API criteria and named-context proposal. Owner paused RTOS and remaining HW stages, recorded as whole-research debt; this pause supersedes historical next steps below. Core and public API unchanged.

- Consumer R18: aggregates/HFA and C++ soft/hard —72 PASS,6 retained FAILs on F411/HLA GDB14/16. Finish/call and const overloads pass; forced Pair return fails delivery in both ABIs, HFA in soft. Small and hard HFA pass, restore PASS in all14 series. Core unchanged; RTOS next.

- Consumer R17: scalar soft/hard-float ABIs —48/48 F411/HLA GDB14/16. Void, double, float and6 arguments verified through finish/return/call, stack and sinks; separate ordinary firmware and FPU initialization without hooks, restore PASS. Previous ELF and core unchanged; structures/HFA and C++ remain next.

- Consumer R16: until/advance/nexti —32/32 F411/HLA GDB14/16 on the unchanged Og ELF. Verified source lines, advance completing at frame exit before its target, nexti interruption by a separate point and explicit continuation; initial scope ERROR retained, restore PASS. Core and firmware unchanged; ABI next.

- Consumer R15: O2/Os —32/32 F411/HLA GDB14/16 on a separate ordinary firmware. Verified inline frames, two locations of one breakpoint, argument loss after an instruction and final outputs; restore PASS. Retained initial startup link failure and offline function disappearance; previous Og ELF unchanged. Core unchanged; navigation next.

- Consumer R14: interception sequences —24/24 F411/HLA GDB14/16 on the unchanged api_firmware. Verified errors/success, retention of accepted results, arguments, counts and selected call order; expected wrong-order rejection retained, restore PASS. Core and firmware unchanged; optimized code next.

- Consumer R13: WFI/SysTick/TIM2 —16/16 F411/HLA GDB14/16 on the unchanged CMSIS ELF. Verified interrupted PC, natural return, distinct wakeup and ticks progress, and delay restoration; restore PASS. Core and firmware unchanged; interception sequences next.

- Consumer R12: DMA/watchpoints —16/16 F411/native DAP GDB14/16 on the unchanged CMSIS ELF. Verified DMA writes without a buffer-watch event, positive CPU controls and final sinks; restore PASS. Core and firmware unchanged; sleep/wakeup next.

- Consumer R11: SysTick/TIM2, hardware exception stack, interrupted context and natural return —16/16 F411/HLA GDB14/16 on the existing CMSIS ELF. Initial FAIL/ERROR retained, optimized_out explicit, restore PASS. Core and firmware sources unchanged; DMA/watchpoints next.

- Consumer R10: fault and timeout of an unfinished dummy call —8+8 expected ERRORs and16/16 positive controls on F411/HLA GDB14/16. Verified diagnostics, pre-timeout sidecar and recovery; original register-name error retained, restore PASS. Further research queue recorded; core and firmware unchanged.

- Consumer R9: interrupted dummy calls and nested result substitution —16/16 F411/HLA GDB14/16. Verified register restoration, persistent RAM effects and natural execution after intervention; restore PASS. Core and firmware unchanged.

- Grouped rc3 GDB Python research under docs/research/rc3-gdb-python: RU/EN plan and reports, JSON results and local indexes. Updated links and CI language-pair checks; result data unchanged.

- Consumer R8: code breakpoint budget and FinishBreakpoint headroom —16/16 HLA GDB14/16 and8/8 native DAP GDB16. Six slots, four guards; continuation after releasing a slot without reset. Original object-lifetime ERROR retained, restore PASS; core and firmware unchanged.

- Consumer R7: watchpoint ranges/budget16/16 and unaligned decomposition8/8 on F411/GDB14/16 native DAP. Confirmed4/5 boundary and unaligned2/4-byte rejection; original FAIL/ERROR retained, restore PASS. Firmware and core unchanged.

- Consumer R6: stack filtering, finish and return in recursion —24/24 F411 GDB14/16. Original callback-expectation failure retained; ABI regression32/32 and old SRET ELF-pin rejection verified. Core unchanged.

- Consumer R5: uint64/float/struct finish and call, scalar return —64/64 F411 GDB14/16; struct return retained FAIL on both versions. Substitution through a reviewed return buffer —8/8. Core unchanged.

- Consumer R4: substitute output buffers and signed status of natural calls; success, error and short response — 32/32 F411 GDB14/16 native DAP, restore PASS. New ordinary firmware without hooks; public API unchanged. Regression retained an ASM ERROR on repeated native DAP stepi; HLA passed4/4 with the same ELF.

- Consumer R3 experiments: breakpoint commands, counter wraparound, same-value watch/awatch, C macros and command composition — 32/32 F411 GDB14/16 native DAP; restore PASS. Core unchanged.

- R2 consumer experiments: navigation, conditional/temporary points, caller, C expressions, return/finish/call and assembly — 56/56 F411 HLA; watchpoints — 8/8 native DAP. Original HLA WATCH failures retained, firmware restored. Core unchanged; promotion requires explicit owner approval.

- Added rc3 R1 consumer prototype for typed snapshots, frames, RAM rollback, ownership and evidence: F411/OpenOCD 48/48 on GDB14/16, expected serialization/timeout errors and restoration verified. Public API/specification unchanged.

- Extended rc3 research with an L0 comparison of GDB14 and xPack GCC15 GDB16, preserving probe evidence; new methods remain unverified on hardware.

- Added bilingual rc3 API research: GDB Python review, 20 experiments for four offered boards and a reproducible GDB14 L0 probe. No new hardware results; runtime/API/specification unchanged.

- Extended HAL F030 to 22 cases: GPIO arguments/filtered call and RCC error/NULL; strict selection of two reviewed source variants, Linux/Windows prepare, specification0.58.

- Reviewed five CMSIS profiles against HAL: 105 and 98 board cases; identified five HAL GPIO/RCC checks to preserve before deleting old profiles. Core and specification unchanged.

- F429 RTC/Sleep/deadline/recovery:20/20 HW +5 repeats, external timeout/recovery and HAL restore PASS; specification0.57.

- F429 ADC/DMA/units/failures:15/15 HW +3 repeats, HAL restored; specification0.56.

- F429 CMSIS baseline:7/7 HW, HAL restored; specification0.55. Fifth CI profile; ADC/RTC remain pending.

- F401 RTC/Sleep/deadline/recovery:20/20 HW +5 repeats, external timeout/recovery and HAL restore PASS; specification0.54. Historical CMSIS snapshot: 4 boards, 78 cases.

- F401 ADC/DMA/units/failures:15/15 HW and three positive repeats, HAL restored; specification0.53.

- F401 CMSIS baseline: 7/7 HW through ST-Link/OpenOCD, HAL boot/blink restored. Flash256/RAM64; ADC/RTC are not migrated yet. Specification0.52.

- README RU/EN badges show a historical CMSIS snapshot: 3 board models, 58 cases and the latest evidence date. Added counting rules and a linked results table; automatic metric publication is not implemented yet.

- F411 CMSIS RTC/Sleep/deadline/recovery group:20/20 HW +5 repeats, external timeout/recovery, HAL restored; specification0.51.

- F411 CMSIS ADC1 CH18/17, DMA2 Stream0, factory arithmetic and state injections as one group.15/15 HW +3 repeats, HAL restored; specification0.50.

- F411 CMSIS clocks/GPIO/SysTick/TIM2 group: 7/7 HW OpenOCD, HAL restored; specification0.49, unchanged API.

- F103 CMSIS: counter/alarm RTC, SysTick/TIM2 Sleep and deadline as one group. 20/20 HW, five repeats, host timeout/recovery and HAL restore; specification0.48. Initial restore access errors retained in evidence.

- F103 CMSIS: ADC1 CH16/17 scan, normal DMA, typical physical units and three state injections. 15/15 HW + 3 positive repeats, HAL restored; specification0.47, API unchanged.

- F103 CMSIS: clocks/GPIO/SysTick/TIM2 group, seven scenarios with macro contracts; 7/7 J-Link HW PASS, HAL restored. rc.2 published at a0d6547; subsequent changes are outside the tag.

## [0.1.0-rc.2] — 2026-10-01

The candidate completed the agreed hardware and integration checks with an ST
server limitation: manual USB reconnection was required. Signed tag published at a0d6547, final CI accepted: [evidence](docs/en/RC2_READINESS.md).

### Fixed

- Repeated `run --package` preserves prior reports and extracts clean sources into a separate session; TC-133.
- F030 CMSIS: exception number through SCB ICSR instead of server-specific xPSR; RTC saves address/mask before changing macro context.

### Verification

- Code 5b7b466: Docs/Offline/Hardware SUCCESS, 27 JSON reports audited; Windows CMSIS F030 18/18, HAL 17/17 with repeats/recovery, three lifecycles at 10/10 each. ST server completed after USB reconnect; uninterrupted sequence not confirmed.
- Consumer fb2d186 / module 67b7431: five profiles/120 CTest in CI; F411/OpenOCD 22/22 and timeout/recovery PASS. Original firmware restored. Specification 0.45; API_VERSION=1.

### Added

- README: historical videos (Russian), Mermaid run layouts and practical GDB/ELF/frame limitations; clarified HAL return-code checks.

- HAL F030: manual run_hw.py with required restore-session; 17/17 HW, six repeats, expected timeout/recovery and HAL restoration passed on ST-Link/OpenOCD. RU/EN protocol, specification 0.40/TC-131; API unchanged.

- Added F030 HAL offline CI level: GCC13, exact inventory/JUnit/JSON and five negative HAL contracts. Docker includes pinned HAL F0; specification0.39/TC-130, API unchanged.

- Standalone tests/hal-f030:17 HAL cases, build without YAML/consumer, provenance/import checks and TECH references. Windows/Linux GCC13 offline19/19. The initial stage was offline; hardware acceptance followed (see above). Specification0.38/TC-129.

- [Techniques catalogue TECH-001…008](docs/en/TESTING_TECHNIQUES.md) with CMSIS scenario references. HAL techniques preserved independently of migration; documentation/comments only, API/specification0.37 unchanged.

- Prepared the [separate F030 HAL regression plan](docs/en/F030_HAL_REGRESSION.md): sources,17 scenarios, limits and four stages. Documentation only; specification0.37/G.13 and API unchanged.

- Owned profiles/examples and new packages use `tests`; old `Tests` inputs remain supported. Local remote stands use ignored `remote.toml` / `<profile>-remote.toml`. Reconfigure after renaming. [Conventions](docs/en/maintenance.md). Specification0.37.

- [F030 HAL→CMSIS mapping and branch batch order](docs/en/F030_CMSIS_ACCEPTANCE.md).

- F030 RTC deadline through argument injection; API unchanged. [Report](docs/en/F030_RTC_DEADLINE.md). Specification0.35.

- F030 busy ADC check; API unchanged. [Report](docs/en/F030_ADC_BUSY.md). Specification 0.34.

- F030 CMSIS RTC: Alarm A/LSI, bounded waits, EXTI17/IRQ; 16/16 HW PASS, HAL restored. Specification0.33; core API unchanged.

- F030 CMSIS Sleep: isolate SysTick/TIM3 and check WFI using interrupted PC; 2/2 new HW PASS, HAL restored. Firmware/API unchanged; specification0.32.

- F030 CMSIS: single-point VDDA/temperature, 7 numeric and 14 invalid vectors; 12/12 HW PASS, HAL restored. libgcc for F030 only; specification0.31, core API unchanged.

- F030 CMSIS ADC/DMA: calibration, CH16/17, normal DMA, raw publication, deadline and missing-IRQ test. 9/9 HW PASS; specification 0.30, API unchanged.

- F030 CMSIS: 100 ms TIM3, NVIC/vector/IRQ, event counter; two new scenarios and CI prepare. 6/6 HW PASS, HAL restored. Specification 0.29; core API unchanged.

- F030 CMSIS baseline: 1 ms SysTick, PA5 LED with a 500 ms interval, explicit
  HSI/GPIO setup; four boot/GPIO/clock/blink scenarios and mandatory CI preparation.
  Nucleo/ST-Link/OpenOCD: 4/4 PASS; previous HAL firmware restored.
  No API/schema changes; specification 0.28, limits in docs/en/F030_CMSIS_BASELINE.md.

- CMSIS example migration plan and F030 gap inventory with acceptance criteria.
  F030 build/offline 3/3 PASS without HW; specification revision 0.27.

- J-Link: `STM32F103CBT6` → `STM32F103CB` mapping (WeAct BluePill-Plus, the stm32-hwtest-bluepill
  demo project); specification revision 0.23.
- Specification revision 0.22: question 11.2.23 on build system independence (a stable
  `session.json` schema with a command to create it, an optional build manifest).
- Release notes `docs/releases/<tag>.md` (starting with v0.1.0-rc.1) — the annotated
  tag message and the GitHub release text; procedure in VERSIONING and maintenance.

### Changed

- Prepared Python version `0.1.0rc2`, API_VERSION=1 and release specification 0.42;
  final candidate acceptance remains pending.

- Documentation reconciled before rc.2: current status, examples, CI and lowercase tests; historical protocols separated from current plans. Specification 0.41 records acceptance/publication rules; the audit stage did not change runtime.

- Renamed the root `Tests` directory to `tests`, updating CI, commands, fixtures
  and links. Consumer profile `Tests` directories and support for both spellings
  remain unchanged. Reconfigure old builds under the new directory.

- The `macros` contract checks the type of the expansion (`whatis`, no memory reads): a type
  missing from the debug info (for example `DBGMCU_TypeDef`) is an ERROR in preflight rather than
  in the scenario; statement macros get a `type_note`. J-Link `STM32F103CBT6` verified on WeAct
  BluePill-Plus. Specification revision 0.25.

### Fixed

- The `macros` contract in C++: the type is taken from the expansion text — `whatis <name>` used
  to give a false `No symbol` ERROR when the compilation unit started with code from a header
  included before the device header (`etl/optional.h` before `main.h`). A compiler command-line
  macro (`-DNAME=value`) counts as defined. Specification revision 0.26.

- Build manifest on CMake 3.25: `compile_commands.json` has no `output` key, the object file is
  taken from the compiler's `-o` (the snapshot used to fail with `KeyError: 'output'`); specification revision 0.24.

## [0.1.0-rc.1] — 2026-09-29

The first release candidate (Python version `0.1.0rc1`, `API_VERSION = 1`, specification revision 0.21).

### Added

- Local stand paths expand `~`, `%VAR%` and `$VAR` (`%USERPROFILE%/.ssh/key`); the scenario
  directory may be named `tests`.
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
  Template `tests/firmware/stands/remote.example.toml`. Checked from Windows to Orange Pi 5:
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
- Hardware check of the CI firmware `tests/firmware/run_hw.py` (10 steps: programming,
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
- CI firmware `tests/firmware` on CMSIS without HAL or stm32-cmake-yml: profiles F030R8
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

- README: features as a list, a table of run layouts with their verification status, MCU
  profiles and verified MCU/debugger/server combinations; STATUS: final check of the candidate.
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

The final check passed on commit `2143665` (CI, hardware runs on the stands, consumer
scenarios) — [before a release](docs/en/VERSIONING.md#before-a-release). The `v0.1.0-rc.1` tag goes on
the commit with the refined documentation: its code is identical to the verified one.
