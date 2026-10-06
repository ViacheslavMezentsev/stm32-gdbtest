# Agent skills

[Русский](README.md)

The skills explain to an AI agent how to apply stm32-gdbtest in a firmware project. Each skill is a
directory with a `SKILL.md` file: a YAML header (`name`, `description`) and instructions in Russian;
the descriptions carry English keywords as well. The skills belong to the same module version as the
submodule and link to its documentation.

| Skill | When |
| --- | --- |
| [stm32-gdbtest-integrate](stm32-gdbtest-integrate/SKILL.md) | attach the module to a project: submodule, `hil/` directory, MCU description, `session.toml`, CMake, presets, stand, first run; moving an older consumer to 0.3.0 |
| [stm32-gdbtest-scenarios](stm32-gdbtest-scenarios/SKILL.md) | write or rewrite a scenario: requirement and contract, stop location, `check(rows)`, `write(rows)`, `ret`, `refused`, `watch`, profile, style, techniques TECH-001…018 |
| [stm32-gdbtest-run](stm32-gdbtest-run/SKILL.md) | run and read the result: `doctor`, host and hw, CLI, remote server, package, CI, `result.json` and logs, common failures |

## Using the skills in a project

The skills live in the submodule: `modules/stm32-gdbtest/skills/`.

- **Claude Code** looks for project skills in `.claude/skills/<name>/SKILL.md`. Copy the three
  directories there (a symbolic link works on Linux and macOS) and refresh the copy with the module
  gitlink:

  ```powershell
  New-Item -ItemType Directory -Force .claude/skills | Out-Null
  Copy-Item -Recurse -Force modules/stm32-gdbtest/skills/stm32-gdbtest-* .claude/skills/
  ```

  ```sh
  mkdir -p .claude/skills && cp -r modules/stm32-gdbtest/skills/stm32-gdbtest-* .claude/skills/
  ```

- **Other agents** (Codex, Gemini and so on): state in the project's `AGENTS.md` that the matching
  `SKILL.md` from `modules/stm32-gdbtest/skills/` is read before integration, scenario writing and runs.

Links inside the skills are relative and lead into the module documentation, so they work from the
submodule; in a `.claude/skills` copy, documentation paths are relative to `modules/stm32-gdbtest/`.

## Changing the skills

The skills are part of the module: a change comes with a CHANGELOG entry and a link check
(`python3 ci/run_checks.py docs`). A new scenario rule goes into the
[techniques catalogue](../docs/en/TESTING_TECHNIQUES.md) and the style test first, then into a skill.
