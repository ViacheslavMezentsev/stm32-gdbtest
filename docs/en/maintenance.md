# Repository maintenance

Documentation → Maintenance · [Русский](../ru/maintenance.md)

This page is the shared procedure for people and AI agents; the entry point is
[AGENTS.md](../../AGENTS.md). Module requirements are not repeated here: their source
is the [technical specification](../TECHNICAL_SPECIFICATION.md) (Russian), whose
current revision is stated in its header.

## Working with the project

**Reading order**

1. [README](../../README.md) (Russian until `README.en.md` is added) — purpose of the
   module, approach and limits.
2. This page: work cycle, branches, commits, bilingual documentation.
3. [TODO.md](../../TODO.md) — current branch, merged changes and next steps.
4. [Technical specification](../TECHNICAL_SPECIFICATION.md): revision history, the
   latest revision's change block, open questions (section 11) and code
   discrepancies (appendix F).
5. For a specific task — the mechanism description in `docs/` ([API](../API.md),
   [contracts](../CONTRACTS.md), [images](../IMAGES.md), [backends](../BACKENDS.md), etc.),
   [current status](../STATUS.md) and the [CHANGELOG](../../CHANGELOG.md).

**Work cycle**

1. Branch `<agent>/<task>` from current main (section "Branches").
2. Behaviour or interface changes: host regression for failure paths, updated
   mechanism description and migration notes ([API](../API.md)), a CHANGELOG entry,
   a new spec revision. Code and tests refer to spec items per appendix D (`# ТЗ 5.9.7`).
3. Local checks of the affected levels (section "Checks").
4. Signed commit, push the branch, match check results to the branch's latest
   commit, merge into main.
5. Record the branch, commit and status in TODO.md.

**Release** (spec 8.9, [versioning rules](../VERSIONING.md)):

1. `__version__` in `stm32_gdbtest/__init__.py`; `API_VERSION` and schema numbers
   change only when the corresponding contract changes.
2. A dated `## [X.Y.Z] - YYYY-MM-DD` section in the CHANGELOG (both languages);
   `[Unreleased]` stays for future changes.
3. A "release" spec revision with up-to-date appendices B and F.
4. Host and offline checks, consumer integration through a real submodule, agreed
   hardware and recovery checks on the final commit.
5. Merge into main, then tag `vX.Y.Z` on the merge commit. Tags are never moved.

**Technical specification**

- Maintained with the [embedded-tech-spec](https://github.com/ViacheslavMezentsev/demo-stm32-skills/tree/main/embedded-tech-spec)
  skill: every edit is a new revision with `(р.X.Y)` marks, a change block and
  updated questions, test cases, matrix and appendices.
- After an edit: `python3 check_spec.py docs/TECHNICAL_SPECIFICATION.md --strict`
  (the skill's `scripts/check_spec.py`) — no errors or warnings.
- An owner's decision goes into a requirement, not only into the questions table.
  Verified and unverified results are distinguished explicitly.
- The specification is written in Russian. No copies are kept outside the
  repository: read the file in the working branch.

## Branches

Changes are made in a branch `<agent>/<task>` from current main. The `<agent>`
prefix is the short lowercase name of the tool or contributor that creates the
branch: `claude/`, `codex/`, `gemini/`, `copilot/`, etc.; a human uses their own
name or `dev/`. A new agent picks its own prefix and does not reuse another's.
`<task>` is a short kebab-case description in English:
`claude/maintenance-rules`, `codex/job-object-supervision`.

One branch — one task. A merged branch is not reused for another task; follow-up
work starts a new branch from the updated main. Pull requests are not used: after
the checks the branch is merged into main with a regular `git merge` (conflicts are
resolved and affected checks repeated), then main is pushed. Force push and
rewriting published history are not allowed. Successful checks of an older commit do not count for new changes.
If CI is added with a branch filter, a new prefix is added to the workflow filter.

## Commits

- Messages follow [Conventional Commits](https://www.conventionalcommits.org/) in English
  (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `refactor:`, `chore:`) with a body
  explaining what and why.
- Commit messages, tag messages and branch names contain no links to chat or
  agent sessions or their discussions; describe the change itself. A
  `Co-Authored-By` trailer is allowed.
- Commits on published branches are signed (SSH or GPG) with a key added to GitHub
  as a **Signing Key**; the author email is a verified address of the account.
  Otherwise GitHub marks the commit Unverified. An agent's signing key is kept
  outside published files (for example, in `.git/`) and can be revoked by the owner
  on GitHub.
- Push, tags and releases are done by the owner, or by an agent explicitly granted
  that right, at an agreed stage. A roadmap entry is not a permission.

## Bilingual documentation

- User documentation is kept in Russian and English (except the specification): `README.md` ↔ `README.en.md`,
  `CHANGELOG.md` ↔ `CHANGELOG.en.md`, `docs/ru/<page>.md` ↔ `docs/en/<page>.md`.
  File names are the same in both languages.
- The Russian version is the source. The English version is updated in the same
  commit; a difference in content is a documentation defect.
- Every page starts with a navigation line and a link to the other language.
  Links to sections of the other language use that page's own anchors.
- Single-language items: the specification (Russian only, not translated), commit
  messages (English), code and code comments (English, except `# ТЗ …` references).
- Existing `docs/*.md` pages move to `docs/ru/` and get English versions step by
  step (spec question 11.2.2); until then links point to the current paths.
- Russian texts use the term «отладчик». The README is a short introduction (why,
  what, how, dependencies, links); exact results and limits go to STATUS, history
  to the CHANGELOG and protocols.

## Checks

1. Module host tests: `python -B -m unittest discover -s Tests/host -v` (Windows).
2. Consumer example without a board: in `examples/minimal-consumer` —
   `cmake --preset debug`, `cmake --build --preset debug`, `ctest --preset offline`.
3. CLI: `python -B -m stm32_gdbtest --version`, `collect`, `trace`.
4. Specification: `check_spec.py --strict`.
5. Hardware checks only under the rules of "Working with hardware". The example's
   full `ctest` programs the MCU.

A build or host PASS is not a hardware PASS. A check report states the exact MCU,
HAL, GDB, backend, ELF and manifest, the effect of halt/reset and the limits of the
evidence. There is no automated CI yet (spec question 11.2.1).

## Working with hardware

1. Before a hardware run, name the board, debugger, backend and connections;
   changing the stand requires the owner's confirmation. Do not infer wiring from
   USB enumeration.
2. Never enable mass erase, option bytes, debugger firmware updates, shared mode or
   Flash breakpoints automatically. After an experiment restore the agreed firmware
   and MCU state.
3. Do not run a third-party server on the same debugger in parallel. The lock only
   coordinates participating runners in one Windows session; after a crash check
   for leftover GDB and server processes.
4. Do not hide ERROR or failure causes; do not rerun automatically to get a PASS.

## Module and consumer boundary

- The module is the infrastructure core. MCU, board, expectations, instruments and
  application tests belong to the consumer project. `Tests/fixtures` are not working
  profiles or evidence of HAL behaviour.
- Do not add test hooks to firmware; `-g3` does not keep unused functions.
- The GDB API is called only from GDB's main thread; the external timeout and
  recovery are kept.
- Mechanism documentation (API, contracts, macros, manifest, backends, identity,
  debugger ownership, images) belongs to this repository. Profile results and
  methodology stay in [stm32-hwtest-blackpill](https://github.com/ViacheslavMezentsev/stm32-hwtest-blackpill):
  link to them, do not copy the experiment log.
- A new consumer build profile is a source of module improvements; the procedure
  is in spec appendix G.

## Workspace and files

- Changes, temporary files and logs stay inside the current workspace. Submodules,
  installed libraries and tools are read and run, not modified without a task.
- Do not commit local stand TOML files, serial numbers, absolute personal paths,
  ELF files, build output or caches.
- In a Windows working copy files may have CRLF (`core.autocrlf`); keep the line
  endings of the file you edit. `.gitattributes` rules are spec question 11.2.11.
