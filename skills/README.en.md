# Agent skills

[Русский](README.md)

The skills explain to an AI agent how to apply stm32-gdbtest in a firmware project. Each skill is a
directory with a `SKILL.md` file following the [Agent Skills specification](https://agentskills.io/specification),
in the same format as [demo-stm32-skills](https://github.com/ViacheslavMezentsev/demo-stm32-skills): a YAML
header with `name` (equal to the directory), `description` (what it does and when to use it), `license: MIT`,
`compatibility` (module version, API_VERSION and the tools needed) and `metadata` (`author`, `version` — the module
version the skill describes — and `api_version`, all values as strings). The text is in Russian, up to 500 lines,
with details in `references/`; the descriptions carry English keywords as well. The host test
`tests/host/test_skills.py` and `skills-ref validate` in the Docs CI check the format. The skills belong to the
same module version as the submodule and link to its documentation.

| Skill | When |
| --- | --- |
| [stm32-gdbtest-integrate](stm32-gdbtest-integrate/SKILL.md) | attach the module to a project: submodule, `hil/` directory, MCU description, `session.toml`, CMake, presets, stand, first run; migrate a consumer to candidate 0.5.0 / API 3 |
| [stm32-gdbtest-scenarios](stm32-gdbtest-scenarios/SKILL.md) | write or rewrite a scenario: requirement and contract, stop location, `check(rows)`, `write(rows)`, `ret`, `refused`, `watch`, `skip`, C++ calls, journal quotas, simulated inputs, profile, style, techniques TECH-001…026 |
| [stm32-gdbtest-run](stm32-gdbtest-run/SKILL.md) | run and read the result: `doctor`, host and hw, CLI, remote server, package, CI, `result.json` and logs, common failures |
| [stm32-gdbtest-results](stm32-gdbtest-results/SKILL.md) | audit saved evidence without a board: artifact order, scenario source, records, JUnit, integrity, export/HTML and justified conclusions; including a pi agent on OrangePi |
| [stm32-gdbtest-report](stm32-gdbtest-report/SKILL.md) | present reviewed evidence to a reader: a compact overview and a technical report as PDF, neutral roles instead of serials and addresses, times with a time zone, plain wording |
| [stm32-gdbtest-stand-loop](stm32-gdbtest-stand-loop/SKILL.md) | deployable stand bundle, finite cycles, FAIL/SKIP policy, STOP and review.json handoff to an agent |
| [stm32-gdbtest-develop](stm32-gdbtest-develop/SKILL.md) | develop firmware through DDTT: plan, scenario before the fix, baseline FAIL, correction, regression and target evidence review |
| [stm32-gdbtest-coverage](stm32-gdbtest-coverage/SKILL.md) | map integration, portable reports, provenance and unknown outcomes. |
| [stm32-gdbtest-renode](stm32-gdbtest-renode/SKILL.md) | short ELF/GDB probes without a board, model limitations and resource cleanup. |
| [stm32-gdbtest-hse-qualify](stm32-gdbtest-hse-qualify/SKILL.md) | qualify physical crystal frequency against tolerance: independent time reference, uncertainty, recovery and DDTT applicability. |


Before a hardware series, use the [scenario checklist](../docs/en/SCENARIO_CHECKLIST.md): it complements scenarios/develop and replaces neither prepare nor board testing.

## TTDD: development driven by testing on target

The module recommends **TTDD** (testing-on-target-driven development): a requirement is confirmed or refuted
by observing the running firmware on the real MCU, not only by a build, a host test or an emulator. DDTT, the
method of this module, is its main tool but not the only one:

> **TTDD = DDTT + other witnesses of the target.**
> The requirement judges, the board answers, and the debugger is only one way to ask.

The letters mirror each other: D²T² (DDTT) answers "how to ask the board through a debugger", T²D² (TTDD)
answers "how to drive development by the board's answers" with any means. The other witnesses are skills of the
companion repository [demo-stm32-skills](https://github.com/ViacheslavMezentsev/demo-stm32-skills). They may not
use a debugger explicitly, but they also work with the target at a low level and cover what DDTT cannot see.

| Witness | What it sees | Effect on the firmware | Skills |
| --- | --- | --- | --- |
| GDB and SWD with stops (DDTT) | state at a stop point: variables, registers, MMIO, returns; injected data and faults | the core halts at breakpoints, target time lags host time | `stm32-gdbtest-*` in this set |
| SWD without halting the core | variables, fields and registers over time while the firmware runs | bus memory reads only | [stm32-diag-record](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-diag-record) (mcap/bag without ROS), [stm32-ros-alt-channel](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-ros-alt-channel) (ROS1) |
| The firmware's own output | log, telemetry and events published by the firmware itself | needs a channel in the firmware (RTT, ITM, UART) | [stm32-rtt-console](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-rtt-console), [stm32-swo-trace](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-swo-trace), [stm32-ros-alt-channel](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-ros-alt-channel) (rosserial) |
| MCU pins from outside | real time: edges, PWM, ISR jitter, UART/I2C/SPI on the wire, start-up | none, a passive probe | [weact-logic-analyzer](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/weact-logic-analyzer) |
| A model without a board | ELF execution on a model, peripheral accesses | none; preparation, not a test on target | `stm32-gdbtest-renode`, [stm32-renode-emulator](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-renode-emulator) |
| Requirements | what to check: requirement and test case IDs, tolerances | — | [embedded-tech-spec](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/embedded-tech-spec) |

Combination rules:

- The expectation comes from the requirement; each witness only confirms or refutes it. Disagreeing witnesses
  are a finding: work out what each of them saw instead of picking the convenient result.
- DDTT halts the core. Measure time, frequencies, jitter and long processes with a witness that leaves the core
  running (analyzer, non-halting SWD, RTT/SWO); keep DDTT for configuration, branches, faults and injection.
  A recording taken during a DDTT scenario shows its stops as gaps; that is a property of the method, not a
  board defect.
- An SWD debugger has one owner: never start two GDB servers on one ST-Link. A DDTT scenario and an SWD
  recording take turns (or share one server when the skill explicitly supports it); the analyzer and a UART
  channel may run in parallel.
- Evidence of one experiment is linked by the scenario or requirement ID and kept together: the DDTT attempt
  (`result.json`), the mcap/bag recording, the analyzer capture, the RTT log. Clocks (host, stand, RTOS ticks)
  are named explicitly.
- An emulator saves attempts on the board, but only the board supports a "verified on target" conclusion.

## Choosing and combining skills

Start with the task instead of loading every skill. Give the agent the project path, module version
and permitted scope; hardware work also needs an up-to-date stand description.

| Skill | Recommended use | Expected result |
| --- | --- | --- |
| `integrate` | First integration or version upgrade. Supply the CMake project and desired tag; verify configuration and prepare before one hardware scenario | Pinned gitlink, HIL configuration, presets and a reproducible run command |
| `scenarios` | A firmware requirement is already defined. Specify observable behaviour and allowed interventions; derive expectations from the requirement, not the current board response | Scenario, requirement and ELF contract, configuration parameters and consistent style |
| `run` | Execute a specific attempt. Supply a session/package and stand; start with doctor and prepare. Code changes belong in `develop`, not unexplained retries | Command and scenario outcomes, logs, recovery and an explanation of FAIL/ERROR/SKIP |
| `results` | Evidence already exists. Supply the complete attempt/campaign and matching sources; check provenance and integrity before interpreting records | Evidence-backed conclusions; arbitrary journal entries are not automatically treated as measurements |
| `report` | The `results` review is finished and a document for a reader is needed. Supply the campaign directories, the `results` conclusions and a description of the objects and stands without serials; neutral JSON first, then the generator | Compact and technical PDF with data provenance; conclusions no stronger than the evidence, incompleteness and limits stated explicitly |
| `coverage` | Source coloring from evidence is needed. Supply the point map, results of one campaign and sources of the same revision; check provenance and unknown outcomes first | LCOV/Cobertura/HTML with separate UNKNOWN and incomplete evidence; coverage is not computed from unconfirmed points |
| `renode` | A short experiment without a board: ELF, a Renode model, GDB. Supply the ELF, the platform description and the goal; name the model limits up front | The outcome on the model and its limits; before "verified on target", the same scenario on a board |
| `stand-loop` | Repeat an accepted immutable bundle. Define finite cycles, FAIL/SKIP policy and STOP; rebuild the bundle when the ELF/scenario changes | Separate attempts, cycle summary and review.json handoff; application sources are not required on the stand |
| `develop` | Change firmware with feedback from the circuit. Supply requirements, sources, stand description and an iteration budget; retain the plan and baseline FAIL before fixing | Requirement → check → fix → regression, preserved failures and explicit evidence boundaries |
| `hse-qualify` | Supply nominal frequency, tolerance, board and allowed operations; establish clock accuracy before hardware measurement | Frequency interval, IN_TOLERANCE/OUT_OF_TOLERANCE/UNKNOWN, separate recovery verdict and epoch scope |

## Typical routes

1. **New project.** [embedded-tech-spec](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/embedded-tech-spec) (requirements and test cases) → `integrate` → `scenarios` → `run` →
   `results`.
2. **Firmware change.** `develop` uses `scenarios`, `run` and `results` at each step; the baseline FAIL is
   recorded before the fix, the regression after it.
3. **Timing requirement** (period, ISR jitter, bus timing). `scenarios`/`run` check the peripheral setup through
   MMIO and SVD → [weact-logic-analyzer](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/weact-logic-analyzer) measures the pin without halting the core → `results` relates both
   witnesses to the requirement. Crystal frequency is the separate `hse-qualify` route with an independent time
   reference.
4. **Behaviour in operation** (telemetry, power cycles, long runs). A DDTT scenario brings the board to a state
   and checks transitions, [stm32-diag-record](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-diag-record) or [stm32-ros-alt-channel](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-ros-alt-channel) records the stream; the
   recording is stored next to `result.json` under the same ID.
5. **No board → board.** `stm32-gdbtest-renode` or [stm32-renode-emulator](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-renode-emulator) for a short experiment and the
   model limits, then the same scenario through `run` on the stand.
6. **Diagnostic channel.** [stm32-rtt-console](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-rtt-console) or [stm32-swo-trace](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/stm32-swo-trace) show what the firmware does between
   stops; they do not replace a DDTT scenario but help explain a FAIL.
7. **Autonomous stand.** `stand-loop` → `results`; a discovered issue becomes a separate `develop` cycle.
8. **Report for a reader.** `run` → `results` → `report`: a compact overview and a technical report as PDF
   from the reviewed evidence. Your own report forms build on `results`.

On OrangePi, result review needs evidence and the matching module version; execution needs a bundle,
GDB/backend and the stand; development additionally needs sources and a compiler.
Selecting a skill does not launch a background agent or grant access to external equipment.

## Using the skills in a project

The skills live in the submodule: `modules/stm32-gdbtest/skills/`.

- **Claude Code** looks for project skills in `.claude/skills/<name>/SKILL.md`. Copy the required
  directories there (a symbolic link works on Linux and macOS) and refresh the copy with the module
  gitlink:

  ```powershell
  New-Item -ItemType Directory -Force .claude/skills | Out-Null
  Copy-Item -Recurse -Force modules/stm32-gdbtest/skills/stm32-gdbtest-* .claude/skills/
  ```

  ```sh
  mkdir -p .claude/skills && cp -r modules/stm32-gdbtest/skills/stm32-gdbtest-* .claude/skills/
  ```

- **Other agents** (Codex, Gemini, pi and so on): state in the project's `AGENTS.md` that the matching
  `SKILL.md` from `modules/stm32-gdbtest/skills/` is read before integration, scenario writing, runs and evidence review.

Links inside the skills are relative and lead into the module documentation, so they work from the
submodule; in a `.claude/skills` copy, documentation paths are relative to `modules/stm32-gdbtest/`.

## Changing the skills

The skills are part of the module: a change comes with a CHANGELOG entry and a link check
(`python3 ci/run_checks.py docs`). A new scenario rule goes into the
[techniques catalogue](../docs/en/TESTING_TECHNIQUES.md) and the style test first, then into a skill.

On OrangePi, the results skill needs only the module checkout and saved artifacts. Point the agent
to SKILL.md in project instructions; no integration with a specific pi shell is required.
Use documentation matching the result producer; missing fields in old formats remain unknown.

For peripheral investigations use the Renode skill [MMIO resource](stm32-gdbtest-renode/references/mmio.en.md): model access logs, followed by authorized target-board validation. Copy the complete skill directory, including references.


[API 3 skill and consumer audit](../docs/archive/pre-060/api3-skills-audit.md) (Russian, P6a, no hardware).
