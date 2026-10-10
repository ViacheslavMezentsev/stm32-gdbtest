# DDTT: debugger-driven testing on target

[Documentation](index.md) → DDTT specification · [Русский](../ru/DDTT.md)

**Debugger-Driven Testing on Target (DDTT), specification 0.3.0 — draft.**

## Abstract

DDTT is a method of verifying embedded software in which test scenarios run on a host
computer and, through a debug interface, control the running firmware on a separate
target device. No test code is added to the firmware: a scenario reaches program
points with breakpoints, reads and compares state using the debug information of the
built image and, when needed, performs explicit injections. This specification
defines terms, principles, a role model and requirements for scenarios, stand
descriptions and tools, so that checks are repeatable, live in the project repository
and run the same way manually, in CI and on a stand in a loop — including when an AI
agent writes the scenarios.

## Status of this document

Draft 0.3.0 of 2026-10-10. The specification is maintained in the
[stm32-gdbtest](https://github.com/ViacheslavMezentsev/stm32-gdbtest) repository, which
is its first (reference) implementation; the specification itself does not depend on
it. Versions follow SemVer: before 1.0 incompatible changes are possible, and each one
is recorded in the [change log](#appendix-b-change-log). The Russian version is the
source; this English version is updated together with it. Feedback goes to the
repository issues.

Normative clarifications in 0.3.0 are proposed for agreement. They do not change released
module contracts, whose sources are the [API specification](../TECHNICAL_SPECIFICATION_API.md)
and [general specification](../TECHNICAL_SPECIFICATION.md).

## 1. Introduction

### 1.1. The problem

In embedded systems code does not run on the machine where it is written and built.
Unit tests on a PC check logic but not peripheral setup, interrupts, clocks, reactions
to driver errors or the behaviour of a specific MCU. Test images with a framework
inside the firmware change the very code under test, its size and memory layout.
Manual checks in a debugger are precise but not repeatable and leave no trace in the
repository. The same applies to checks an AI agent performs in a chat through a
debugger: the result stays in the conversation, not in the project.

### 1.2. The idea

A debugger already does everything needed to observe running firmware: stop it at the
right point, read variables, structures and registers using debug information, change
a value and resume. DDTT turns these actions into a scenario — a file in the
repository with an identifier, a time limit and expectations — that a tool runs on a
stand and that yields an unambiguous verdict and a machine-readable report.

### 1.3. Scope

DDTT applies when **the target device is separate from the host** and reachable through
a debug interface: microcontrollers and SoCs with SWD, JTAG, cJTAG or a similar port,
connected through a debug adapter and a debug server (for example GDB RSP). Typical
targets are Cortex-M, RISC-V and DSP MCUs, bare metal or with an RTOS.

The name reflects this split. **Debugger-driven testing** is the general notion: a
scenario controls the code under test through a debugger. It also applies to PC
programs, where the debugger and the code run on the same machine and OS. **DDTT**
(debugger-driven testing **on target**) is its variant for a separate target device, the
subject of this specification. The general notion is written in full without an
abbreviation: DDT is already taken (section 9).

Out of scope:

- debugging and testing processes on the same machine and OS as the tool (ordinary PC
  program debugging, including GDB on a Linux process);
- simulation and emulation of the target (they complement DDTT but are not DDTT);
- test frameworks running inside the firmware;
- control of the device environment (power, stimuli, instruments) — that is HIL; DDTT
  can be a part of it, see section 9.

## 2. Conformance

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT** and **MAY** are to be
interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) when, and only when, they appear in
bold. Sections 1, 9–11 and the appendices are informative; sections 2–8 are normative.

Conformance classes:

| Class | What conforms | Requirements |
| --- | --- | --- |
| DDTT scenario | A test scenario file of a project | 6.1 |
| DDTT stand description | A local description of the connection | 6.3 |
| DDTT tool | A runner that executes scenarios | 6.2, 6.4–6.8 |
| DDTT agent | An AI agent that writes and runs scenarios | 7 |

A tool conforms to **DDTT Core** if it meets all **MUST** requirements of sections 6.2,
6.4, 6.5, 6.6 and 6.8 except those marked as optional capabilities. Optional
capabilities are declared separately:

| Capability | Requirements |
| --- | --- |
| DDTT-Image — image verification and programming, full image | DDTT-6.4-4…DDTT-6.4-6 |
| DDTT-Preflight — checks without hardware | 6.7 |
| DDTT-Remote — debug server on a stand host | DDTT-6.3-4…DDTT-6.3-6 |
| DDTT-Skip — explicit scenario inapplicability | DDTT-6.5-6 |

Requirements have permanent identifiers `DDTT-<section>-<number>` (for example
DDTT-6.1-1); numbers are never reused.

## 3. Terms

| Term | Definition |
| --- | --- |
| Debugger-driven testing | The general notion: a scenario controls the code under test through a debugger — on a PC or on a separate device. No abbreviation is used. |
| DDTT | Debugger-driven testing on a separate target device (debugger-driven testing on target) — the subject of this specification. |
| Host | The computer where the tool runs and the scenario executes. |
| Target device (target) | A separate device with the firmware under test (MCU, SoC), reachable through a debug interface. |
| Debug adapter | A device connecting a computer to the target's debug port (ST-Link, J-Link, CMSIS-DAP and similar). |
| Debug server | A program giving a debugger access to the target through the adapter (OpenOCD, J-Link GDB Server and similar). |
| Debug agent | The part of the tool that executes the scenario inside the debugger or through its API. |
| Image | The built firmware artifact with debug information (for example ELF with DWARF) and binary data derived from it. |
| Scenario | A unit of verification: an identifier, metadata and actions on the target through the target API. |
| Target API | Operations available to a scenario: reaching a program point, reading and comparing state, explicit injections. |
| Stand | A specific combination of target, adapter, server and their connection, described locally. |
| Stand host | The computer the adapter is connected to, when it differs from the host. |
| Stand layout | The distribution of the tool, debugger, server and adapter across computers. |
| Run | One execution of one scenario on one stand. |
| Verdict | Scenario outcome: PASS, FAIL, ERROR; also SKIP with DDTT-Skip. Command exit additionally reflects required-artifact failures. |
| Preflight | Checks of the image, contracts and stand without accessing the target. |
| Injection | An explicit change of target state by a scenario (writing a value, forcing a function return). |
| Debugger influence | A change of target behaviour caused by halts, resets and injections. |

## 4. Principles

1. **Firmware without test code.** The image under test is the one that will run in the
   product, or built closely to it; no test hooks are added.
2. **Artifact identity.** The tool proves that the target runs exactly the image whose
   debug information the scenario was written against.
3. **Repeatability.** A scenario is a file in the project's version control, not an
   action in an interactive session.
4. **Stand independence.** One scenario runs with any stand layout; the stand is
   described separately and locally.
5. **Honest verdict.** An expectation mismatch (FAIL) differs from an infrastructure
   failure (ERROR); ERROR never becomes PASS.
6. **Explicit influence.** Halts, resets and injections are declared and recorded in the
   report; DDTT does not pretend to be a non-intrusive measurement.
7. **Bounded execution.** Every run is time-limited and ends with an attempt to return
   the target to operation.
8. **Hardware safety.** Irreversible actions (mass erase, option bytes, adapter firmware
   updates) are never performed implicitly.

## 5. Model

```mermaid
---
config:
  look: classic
---
flowchart LR
    S["Scenario in the repository"] --> R["Tool (runner)"]
    I["Image with debug information"] --> R
    D["Stand description (local)"] --> R
    R --> A["Debug agent: target API"]
    A <--> V["Debug server"]
    V <--> P["Debug adapter"]
    P <-->|"SWD / JTAG"| T["Target device"]
    R --> O["Report: verdict and evidence"]
```

The tool reads the scenario, the image and the stand description, performs preflight
checks, obtains exclusive access to the adapter, starts the server and the agent,
verifies that the target and image match, executes the scenario, recovers the target
and writes the report. The server and adapter may be on a stand host; the connection
to it is then an authenticated channel (section 6.3).

## 6. Requirements

### 6.1. Scenario

- **DDTT-6.1-1.** A scenario **MUST** have a stable identifier unique within the project
  and **MUST** be stored in the project's version control.
- **DDTT-6.1-2.** Scenario metadata (identifier, time limit, labels, required contracts)
  **MUST** be available to the tool without executing scenario code.
- **DDTT-6.1-3.** A scenario **MUST** access the target only through the target API and
  **MUST NOT** contain commands of a specific debug server or adapter.
- **DDTT-6.1-4.** A scenario **MUST NOT** contain stand-specific data (serial numbers,
  addresses, paths, credentials).
- **DDTT-6.1-5.** A scenario **SHOULD** reference the project requirement it verifies;
  the tool **SHOULD** check that references and requirements match.
- **DDTT-6.1-6.** A scenario **MUST** express expectations as checks with a name, an
  actual and an expected value.

### 6.2. Target API

- **DDTT-6.2-1.** The API **MUST** allow reaching a given program point (a function or an
  address) and verify the stop reason and location.
- **DDTT-6.2-2.** The API **MUST** allow reading values, structure fields and registers
  using the image's debug information and **MUST** refuse when a value is unavailable
  (for example optimized out) instead of returning an arbitrary result.
- **DDTT-6.2-3.** Breakpoints **SHOULD** be hardware breakpoints; the tool **MUST** respect
  the number available on the target.
- **DDTT-6.2-4.** Injections **MUST** be explicit API operations and **MUST** be recorded in
  the report with values before and after.
- **DDTT-6.2-5.** Before a scenario runs, the target **MUST** be brought into a defined
  state (for example reset and halted at the application entry point).

### 6.3. Stand description

- **DDTT-6.3-1.** A stand description **MUST** be separate from scenarios and **MUST NOT** be
  published with the project when it contains data about specific hardware.
- **DDTT-6.3-2.** The adapter **MUST** be selected explicitly (for example by serial
  number), not by connection order.
- **DDTT-6.3-3.** Changing the stand **MUST NOT** require changing scenarios.
- **DDTT-6.3-4.** (DDTT-Remote) When the server runs on a stand host, the connection
  **MUST** be authenticated and encrypted with host authenticity verification; the server
  **SHOULD** listen only on the stand host's local interface.
- **DDTT-6.3-5.** (DDTT-Remote) A stand description **MUST NOT** contain passwords; a run
  **MUST NOT** wait for interactive input.
- **DDTT-6.3-6.** (DDTT-Remote) Losing the connection to the stand host **MUST** stop the
  server and release the adapter on the stand host.

### 6.4. Run lifecycle

- **DDTT-6.4-1.** The tool **MUST** perform a run in this order: input validation →
  exclusive adapter access → preflight → server start → connection → target check →
  image preparation → scenario → teardown → report.
- **DDTT-6.4-2.** The tool **MUST** work with an immutable copy of the image for the
  duration of the run.
- **DDTT-6.4-3.** Before accessing image memory the tool **MUST** check that the target
  matches its profile (for example by the device identifier register and memory size)
  and, according to the project policy, warn or refuse on mismatch.
- **DDTT-6.4-4.** (DDTT-Image) The tool **MUST** compare target memory with the image's
  load sections and state explicitly in the report what was verified (sections, the
  full range, a checksum).
- **DDTT-6.4-5.** (DDTT-Image) Image programming **MUST** follow the stand policy; a
  verify-only mode **MUST NOT** program the image or erase its range. This restriction
  applies to image preparation, not to declared scenario injections or debugger
  control operations.
- **DDTT-6.4-6.** (DDTT-Image) Irreversible operations (mass erase, option bytes, read
  protection) **MUST NOT** be performed without explicit instruction.
- **DDTT-6.4-7.** Scenario execution **MUST** be limited by an external time limit
  enforced by the host, not by the scenario.
- **DDTT-6.4-8.** On any outcome the tool **MUST** attempt to return the target to
  operation (reset and run) and stop all started processes including children; the
  recovery result **MUST** be in the report.

### 6.5. Verdict and report

- **DDTT-6.5-1.** The verdict **MUST** be one of: PASS — all checks passed; FAIL — a
  scenario check did not match; ERROR — an input, infrastructure or target failure or an
  unexpected exception. With DDTT-Skip, SKIP is also allowed: explicit scenario
  inapplicability with a reason; it is not PASS.
- **DDTT-6.5-2.** The tool **MUST** produce a machine-readable report (for example JSON and
  JUnit XML) on any outcome once the run has started and return an exit code matching
  the verdict and mandatory artifact-processing failures (DDTT-6.5-7).
- **DDTT-6.5-3.** The report **MUST** contain the scenario identifier, the image hash, the
  checks, the evidence scope of image verification, the injections performed and the
  teardown method.
- **DDTT-6.5-4.** The report **SHOULD** contain the debugger, server and adapter versions
  observed during the run and **MUST NOT** contain credentials or personal paths.
- **DDTT-6.5-5.** Logs of all started processes **MUST** be kept next to the report.

- **DDTT-6.5-6.** (DDTT-Skip) Skipping **MUST** end the scenario with a non-empty reason,
  retain available evidence and perform normal teardown. SKIP **MUST NOT** replace an
  established FAIL/ERROR and **MUST NOT** count as a completed check.
- **DDTT-6.5-7.** When mandatory artifact processing has a separate outcome, the tool
  **MUST** preserve the scenario outcome and artifact error separately; the command
  **MUST** signal that processing error even when the scenario passed.

### 6.6. Exclusive access

- **DDTT-6.6-1.** The tool **MUST** obtain exclusive access to the adapter before first
  accessing it and hold it until the server has stopped.
- **DDTT-6.6-2.** A busy adapter **MUST** give ERROR without waiting and without accessing
  the target.
- **DDTT-6.6-3.** Signs that a previous owner crashed **SHOULD** be detected and reported
  without killing foreign processes or resetting the target.

### 6.7. Preflight (DDTT-Preflight)

- **DDTT-6.7-1.** All steps that do not need the target (image, build provenance,
  contracts, stand description, binary data preparation) **MUST** be available as a
  separate mode that does not access the adapter.
- **DDTT-6.7-2.** Contracts — declarative expectations about the image (functions, types,
  fields, enumeration values, macro expansions) — **MUST** be checked before the server
  starts; an unmet contract **MUST** give ERROR.
- **DDTT-6.7-3.** The preflight mode **SHOULD** be used in CI without hardware.

### 6.8. Automation

- **DDTT-6.8-1.** The tool **MUST** run non-interactively from the command line and
  **SHOULD** integrate with the project's build and test system.
- **DDTT-6.8-2.** The same scenario **MUST** run unchanged manually, in a CI runner and in a
  repeated loop on a stand.
- **DDTT-6.8-3.** The tool **SHOULD** provide stand environment diagnostics without
  accessing the target.

## 7. Scenarios created by agents

- **DDTT-7-1.** A check performed by an AI agent **MUST** be written as a scenario per
  section 6.1 and stored in the repository; a result in a conversation is not a check.
- **DDTT-7-2.** An agent **MUST** run preflight before running on hardware and **MUST** hand
  the run report to a person, not its own retelling.
- **DDTT-7-3.** An agent **MUST NOT** change the stand, the adapter firmware or irreversible
  target settings without the stand owner's confirmation.
- **DDTT-7-4.** An agent **MUST NOT** rerun to obtain a PASS or hide an ERROR.

## 8. Security considerations

- Debug access gives full control over the target; network-reachable stands **MUST** be
  protected like administrative access: keys instead of passwords, host authenticity
  verification, the server on the local interface only.
- Stand descriptions contain serial numbers, addresses and paths and are not published.
- Injections may cause dangerous behaviour of connected equipment (motors, power
  circuits); the scenario author is responsible for the safety of an injection, the
  stand owner for whether experiments are acceptable on it.
- Debugger influence changes timing; DDTT does not replace measurements of time,
  current and signals.

## 9. Relation to other approaches (informative)

| Approach | Difference from DDTT |
| --- | --- |
| Unit tests on a PC (SIL) | Check logic off-target; DDTT checks the running firmware on the target |
| Tests inside the firmware (Unity, Ceedling on target, Zephyr Twister) | Add test code to the image; DDTT leaves the image unchanged |
| Processor-in-the-Loop (PIL) | Runs generated code on the target processor and compares with a model; DDTT checks the project firmware through the debugger |
| Hardware-in-the-Loop (HIL) | Controls the device environment (stimuli, load, power); DDTT observes and acts from inside through the debug port. DDTT combined with environment control gives full HIL |
| Board farm control (labgrid and similar) | Power, console and flashing of stands; DDTT can use such a farm as a stand |
| Manual debugging, debugger scripts | The same actions without repeatability, a verdict or a report |

The abbreviation DDTT should not be confused with DDT — data-driven testing, the Python
`ddt` library and the Linaro DDT debugger.

## 10. Implementation in stm32-gdbtest 0.4.1 (informative)

Baseline: published package **0.4.1**, `API_VERSION=2`, `target.toml` schema 2;
general specification 0.95, API specification 0.3.16. **This DDTT specification 0.3.0**
has an independent version. Evidence is v0.4.1 source and accepted reports, not new hardware runs.

The module provides Core, Image, Preflight, Remote and Skip mechanisms. This is an implementation
map, **not a claim that every MUST is fully satisfied**; gaps are listed in 10.6.
Method requirements are not weakened simply to match current code.

### 10.1. Roles and inputs

| Role | Implementation artifact | Responsibility |
| --- | --- | --- |
| Requirement and scenario | Python with `@case`, stable ID and requirements.md entry; metadata collected without import | Firmware project |
| Session configuration | `session.toml`: `config.target`, `config.api`, optional `config.image` policy, result capture | Firmware project |
| MCU | `target.toml`: memory, identity, points, fault guards, backend reset dialects; not a stand serial | Firmware project |
| Parameters | `api.toml`: API settings and project data; available through `t.profile`, including `t.profile.user` | Scenario author |
| Image and provenance | ELF/DWARF, build manifest; generated `session.json` connects build to runner | Build/CMake |
| Connection | Local TOML; `*.local.toml`, `<profile>-<backend>.remote.toml`; no published secrets | Stand owner |
| Executor | Host Python → GDB-Python → OpenOCD, ST-LINK GDB Server, st-util or J-Link | Module and environment |
| Portable input | `pack` creates input for `run --package`; the local stand is selected separately | Build host / operator |

`session.toml` is source configuration, `session.json` a generated build artifact,
`result.json` one attempt's result. They are not interchangeable. A package runs scenarios
on OrangePi without the project; changing firmware needs sources and a compiler.
[Configuration/CLI](API.md), [manifests](MANIFESTS.md), [run layouts](RUN_LAYOUTS.md).

### 10.2. Requirements and tools

| Requirements | 0.4.1 mechanisms | Evidence to inspect |
| --- | --- | --- |
| 6.1 | `@case`, collect, traceability, contracts | Requirement ID, selected scenario and ELF |
| 6.2 | Target and GDB-Python; [reference](api/index.md) | Stop reason/location, values, current frame and MCU resources |
| 6.3 | [Backends](BACKENDS.md), [SSH](LINUX_STAND.md) | Board/profile/probe match; doctor alone does not check the MCU |
| 6.4 | [runner.py](../../stm32_gdbtest/runner.py), [agent.py](../../stm32_gdbtest/agent.py) | ELF snapshot, identity, image verification, failure phase, teardown/recovery |
| 6.5 | [reports.py](../../stm32_gdbtest/reports.py), [result_capture.py](../../stm32_gdbtest/result_capture.py) | Verdict, command code, capture and integrity separately |
| 6.6 | [Debugger ownership](DEBUGGER_OWNERSHIP.md) | One owner; stand-host lock; no killing foreign processes |
| 6.7 | `run --prepare-only`, [contracts](CONTRACTS.md) | No server; NOT_REQUESTED is not a passed contract |
| 6.8 | CLI, CTest, doctor, [stand_loop.py](../../tools/stand_loop.py) | Same package; separate attempts; explicit SKIP policy |
| 7 | [Develop skill](../../skills/stm32-gdbtest-develop/SKILL.md) | Plan, requirement-specific baseline FAIL, fix, regression, restoration |

| Scenario task | Tools | Boundary |
| --- | --- | --- |
| Navigation | `reach`, `resume`, `step`, `until`, `finish`, `reset` | finish executes the rest of a function; ret forces its return; inspect stop results and inferred_stop |
| Points | `breakpoint`, `watch`, Point objects | Hardware budget, function prologue, optimization and watchpoint delay |
| State | `read`, `evaluate`, `memory`, `registers`, `frames`, `locals`, `symbol` | frames is the current stack, not a historical call tree; MMIO reads can have effects |
| Assertions | `check`, `check(rows)`, matchers, `refused` | Requirement-derived expectations; an expected exception does not prove absence of partial effects |
| Injections | `write`, `write(rows)`, memory writes, `ret`, `call` | No general transaction/rollback; calls and expressions can execute firmware |
| Evidence | `profile`, `record`, `records`, `skip` | Arbitrary journal; skip ends a scenario, not a block or other tests |
| Low-level access | `execute`, direct GDB-Python | Supported, but dependencies and untracked effects limit portability |

Direct GDB-Python does not automatically constitute a portable class-6.1 scenario: the author
assesses DDTT-6.1-3 and retains observations separately. execute records command metadata,
not all side effects. GDB APIs run on GDB's main thread. [Techniques](TESTING_TECHNIQUES.md)
separate Python/GDB composition from Target methods: gdb.Value, disassembly and series
calculations do not need a new Target method for every technique.

Shipped examples: [events and intervals](../../tests/firmware/common/tests/board/test_event_intervals.py),
[event injection](../../tests/firmware/common/tests/board/test_event_injection.py),
[watchpoint](../../tests/firmware/common/tests/board/test_watch.py),
[conditional SKIP](../../tests/firmware/common/tests/board/test_release040_skip.py).
Their expectations belong to the CI firmware; an application needs its own requirements.

### 10.3. One run

1. Build ELF, manifest and session; declare expected outcomes and restoration firmware.
2. Run doctor and prepare: environment and input checks, not HW PASS.
3. The runner creates a unique attempt directory, snapshots ELF/configuration, checks inputs
   and contracts; the hardware path uses exclusive probe ownership.
4. Start backend/GDB, check identity and declared image scope, reset/halt and execute the
   scenario. Identity warn is weaker than strict.
5. With capture enabled, the agent attempts to save records before closing Target, then
   performs teardown. On failure/timeout the host separately attempts recovery.
6. The host writes final JSON/JUnit, validates capture and returns the command code.
   Restoring the agreed ELF is checked separately: reset_run is not firmware restoration.

These are responsibilities; runner/agent define exact failure branches. Prepare bypasses
the hardware lock and server. Early failures leave some fields/logs absent. Power loss,
USB failure or forced termination can leave the target state unknown.
Commands, run passports and restoration: [local CI, L6](local-ci.md).

### 10.4. Outcomes and artifacts

| Scenario outcome | Meaning | Usual command code |
| --- | --- | --- |
| PASS | Scenario completed, assertions passed | 0 |
| FAIL | An assertion failed | 1 |
| ERROR | Input, execution, infrastructure or teardown error | 2 |
| SKIP | Explicit inapplicability with a reason | 77 |

Required capture failure makes command_code=2 even with status=PASS or SKIP; the scenario
outcome is retained and JUnit adds an infrastructure error. Do not infer success from status
alone, stdout or the largest numeric code. Teardown failure can change the outcome to ERROR
regardless of earlier successful checks.

| Artifact | Purpose and limits |
| --- | --- |
| `result.json`, `junit.xml` | Final host result: mode, ID/run_id, checks, image evidence, diagnostics and completion according to the reached phase |
| `agent-result.json` | Internal GDB result; not a substitute for host reporting after cleanup and capture validation |
| `firmware.elf`, manifest, `config.json`, logs | Inputs/provenance; availability depends on phase and mode; some data is local |
| `records.json` | With `[results] capture = true` in session.toml; schema, run_id, case_id, records; hash and ownership checked |
| `index.json`, `export.json`, CSV | External export of explicitly selected attempts; records/projections, not a new MCU verdict |
| JSON/HTML summary | Data presentation; missing/changed files differ from firmware FAIL |
| Stand-cycle `review.json` | Agent input; cycle policy does not replace individual run outcomes |

record(name, data) snapshots arbitrary data. The author chooses its name; sequence is order,
not time. Measurements need explicit units, sampling context and conversions; the scenario
calculates mean/standard deviation. Record observations before potentially terminating checks.
Hard interruption can prevent capture; unavailable/error does not mean an empty successful journal.
[Export](RESULTS.md), [interpretation skill](../../skills/stm32-gdbtest-results/SKILL.md).

### 10.5. Repetition and external equipment

stand_loop.py executes a finite TOML plan of accepted packages, retains attempts, handles STOP
and expected SKIP. This operates an immutable package, not an agent editing firmware.
All-SKIP does not establish device testing. Version 0.4.1 has no dynamic dependency tree or
automatic disabling of other branches based on records; scenarios have no automatically shared journal.

Power supplies, loads, telemetry and instruments use external tools under an agreed plan.
The module provides diagnostics and results, not a universal equipment-control protocol.
A systemd service and autonomous pi/Qwen integration have not been established by stand_loop
testing. [Stand cycles](STAND_LOOP.md).

### 10.6. Open conformance boundaries

| Requirement | 0.4.1 evidence and further checks |
| --- | --- |
| 6.2-4, 6.5-3: all injections before/after | write/memory and mutations provide partial data; ret, call, side-effecting evaluate and raw GDB do not snapshot every effect. Completeness needs an audit; scenarios explicitly record relevant values meanwhile |
| 6.5-4: no personal paths | Local tracebacks, configuration and logs can contain paths/addresses. Full sanitization is not guaranteed; inspect before publication. This is a draft gap, not permission to delete original evidence |
| 6.3-6, 6.4-8: cleanup/recovery | SSH helper, watchdog and finally implement attempts; power/USB/network loss prevents guaranteed recovery. Test failure configurations; unknown is not success |
| 6.5-2: report on every failure | Handled after run-directory creation; disk-write failure/process termination can prevent complete artifacts. Missing reports remain error/unknown evidence |
| 6.2-1: stop reason | Some GDB versions use inferred reasons with warnings. Check location/data too; inference is not an explicit server event |
| Complete hardware acceptance | Specific combinations are accepted; extended F411/F030/ST-LINK GDB Server suites are limited by USB ERROR |

These are audit tasks, not new API promises or proof that all other MUSTs have been met.
[Acceptance](API_ACCEPTANCE.md), [0.4.0 scenarios](API040_SCENARIOS.md) and [metrics](HARDWARE_METRICS.md)
retain versions, configurations and limitations.

## 11. Development with target feedback (informative)

The plan specifies the requirement, observable assertion, allowed changes, stand, injections,
iteration budget and restoration firmware.

1. Retain revisions, configuration, ELF/manifest and scenario. Derive expectations from requirements.
2. Obtain the target FAIL. Connection/contract ERROR does not establish a defect. If the original
   image is unavailable, note the missing baseline; do not break code just to get red.
3. Fix the application, build a new ELF and repeat the same check. Preserve the old FAIL;
   explain criterion changes separately, never weaken expectations merely to get PASS.
4. Check adjacent scenarios and agreed board variants. Suppressing IRQ models a missing notification,
   not a physical DMA fault or free-running timing deadlines.
5. Confirm restoration, review artifacts and stop within the budget. Resolve stand issues first
   after USB ERROR, wrong identity or failed restoration.

Practice in [STATUS](STATUS.md): BluePill F103CB ADC cleanup after early POST failure;
BlackPill F411/F401 retention of a timeout diagnostic code. Baseline FAIL, fixes and regression
were used without test hooks. These are individual verified cycles, not proof of general agent autonomy.

The [develop skill](../../skills/stm32-gdbtest-develop/SKILL.md) defines the procedure;
[scenarios](../../skills/stm32-gdbtest-scenarios/SKILL.md), [run](../../skills/stm32-gdbtest-run/SKILL.md)
and [results](../../skills/stm32-gdbtest-results/SKILL.md) detail its steps. Accepted changes get
a new package and a separately agreed repetition plan.


## Appendix A. Example scenario (informative)

The example uses the common CI firmware and ci_app_api contract: app_loop, app_step and
app_state. Two finish calls correspond to its producer and caller wrapper, specific to
this firmware. Based on the [verified records scenario](../../tests/firmware/common/tests/board/test_release040_records.py).
Add a project requirement for HW_APP_STEP; other ELFs need their own symbols and contract.

```python
"""
RU: Проверка шага приложения и сохранение состояния.
EN: Check an application step and retain its state.
"""
from stm32_gdbtest import case, one_of


# Observe one application step and retain evidence for the report.
@case("HW_APP_STEP", contracts=("ci_app_api",))
def app_step(t):
    enabled = t.profile.user.get("sample_step", True)
    t.check("sample_step is boolean", type(enabled) is bool)
    if not enabled:
        t.skip("sample_step disabled in api.toml")

    # Read named fields, then stop after the producer and its wrapper return.
    t.reach("app_loop")
    before = t.read("app_state", fields={"ticks": None, "led": None})
    t.reach("app_step")
    t.finish()
    t.finish()
    after = t.read("app_state", fields={"ticks": None, "led": None})
    t.record("app.step", {"before": before, "after": after})

    # Check the increment with unsigned wraparound and the allowed LED states.
    t.check([
        ("one step published", (after["ticks"] - before["ticks"]) & 0xFFFFFFFF, 1),
        ("LED state", after["led"], one_of(0, 1))
    ])
```

To retain the journal on disk, in session.toml:

```toml
[results]
capture = true
```

Inspect result.json and capture afterwards; a record does not replace an assertion.
sample_step=false expects SKIP, not evidence of MCU behavior. No new hardware run is
claimed for this DDTT revision.

## Appendix B. Change log

| Version | Date | Changes |
| --- | --- | --- |
| 0.3.0 | 2026-10-10 | Aligned with package 0.4.1: DDTT-Skip (6.5-6), artifact outcome (6.5-7; clarified 6.4-5 and 6.5-1/2), implementation/gap map, development loop and example. Existing IDs retained; module API unchanged |
| 0.2 | 2026-09-28 | Name refined: Debugger-Driven Testing on Target instead of Debugger-Driven On-Target Testing; the general notion "debugger-driven testing" introduced, DDTT is its variant for a separate target device (1.3, 3). Requirements unchanged |
| 0.1 | 2026-09-28 | First draft: scope, terms, principles, model, requirements for scenarios, the target API, stands, the run lifecycle, reports, access, preflight, automation and agent scenarios; the stm32-gdbtest reference implementation |
