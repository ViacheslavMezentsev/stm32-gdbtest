# Agent skills

[Русский](README.md)

The skills explain to an AI agent how to apply stm32-gdbtest in a firmware project. Each skill is a
directory with a `SKILL.md` file: a YAML header (`name`, `description`) and instructions in Russian;
the descriptions carry English keywords as well. The skills belong to the same module version as the
submodule and link to its documentation.

| Skill | When |
| --- | --- |
| [stm32-gdbtest-integrate](stm32-gdbtest-integrate/SKILL.md) | attach the module to a project: submodule, `hil/` directory, MCU description, `session.toml`, CMake, presets, stand, first run; migrate an older consumer to released 0.4.0 |
| [stm32-gdbtest-scenarios](stm32-gdbtest-scenarios/SKILL.md) | write or rewrite a scenario: requirement and contract, stop location, `check(rows)`, `write(rows)`, `ret`, `refused`, `watch`, `skip`, profile, style, techniques TECH-001…019 |
| [stm32-gdbtest-run](stm32-gdbtest-run/SKILL.md) | run and read the result: `doctor`, host and hw, CLI, remote server, package, CI, `result.json` and logs, common failures |
| [stm32-gdbtest-results](stm32-gdbtest-results/SKILL.md) | audit saved evidence without a board: artifact order, scenario source, records, JUnit, integrity, export/HTML and justified conclusions; including a pi agent on OrangePi |
| [stm32-gdbtest-stand-loop](stm32-gdbtest-stand-loop/SKILL.md) | deployable stand bundle, finite cycles, FAIL/SKIP policy, STOP and review.json handoff to an agent |
| [stm32-gdbtest-develop](stm32-gdbtest-develop/SKILL.md) | develop firmware through DDTT: plan, scenario before the fix, baseline FAIL, correction, regression and target evidence review |

## Choosing and combining skills

Start with the task instead of loading every skill. Give the agent the project path, module version
and permitted scope; hardware work also needs an up-to-date stand description.

| Skill | Recommended use | Expected result |
| --- | --- | --- |
| `integrate` | First integration or version upgrade. Supply the CMake project and desired tag; verify configuration and prepare before one hardware scenario | Pinned gitlink, HIL configuration, presets and a reproducible run command |
| `scenarios` | A firmware requirement is already defined. Specify observable behaviour and allowed interventions; derive expectations from the requirement, not the current board response | Scenario, requirement and ELF contract, configuration parameters and consistent style |
| `run` | Execute a specific attempt. Supply a session/package and stand; start with doctor and prepare. Code changes belong in `develop`, not unexplained retries | Command and scenario outcomes, logs, recovery and an explanation of FAIL/ERROR/SKIP |
| `results` | Evidence already exists. Supply the complete attempt/campaign and matching sources; check provenance and integrity before interpreting records | Evidence-backed conclusions; arbitrary journal entries are not automatically treated as measurements |
| `stand-loop` | Repeat an accepted immutable bundle. Define finite cycles, FAIL/SKIP policy and STOP; rebuild the bundle when the ELF/scenario changes | Separate attempts, cycle summary and review.json handoff; application sources are not required on the stand |
| `develop` | Change firmware with feedback from the circuit. Supply requirements, sources, stand description and an iteration budget; retain the plan and baseline FAIL before fixing | Requirement → check → fix → regression, preserved failures and explicit evidence boundaries |

Typical routes:

- New project: `integrate` → `scenarios` → `run` → `results`.
- Firmware change: `develop` uses `scenarios`, `run` and `results` at each iteration.
- Autonomous stand: `stand-loop` → `results`; a discovered issue becomes a separate `develop` cycle.

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
