# Repository maintenance

[Documentation](index.md) → Maintenance · [Русский](../ru/maintenance.md)

This page is the shared procedure for people and AI agents; the entry point is
[AGENTS.md](../../AGENTS.md). Module requirements are not repeated here: their source
is the [technical specification](../TECHNICAL_SPECIFICATION.md) (Russian), whose
current revision is stated in its header.

## Working with the project

**Reading order**

1. [README](../../README.en.md) — purpose of the
   module, approach and limits.
2. This page: work cycle, branches, commits, bilingual documentation.
3. [TODO.md](../../TODO.md) — current branch, merged changes and next steps.
4. [Technical specification](../TECHNICAL_SPECIFICATION.md): revision history, the
   latest revision's change block, open questions (section 11) and code
   discrepancies (appendix F).
5. For a specific task — the mechanism description in `docs/` ([API](API.md),
   [contracts](CONTRACTS.md), [images](IMAGES.md), [backends](BACKENDS.md), etc.),
   [current status](STATUS.md) and the [CHANGELOG](../../CHANGELOG.en.md).

**Work cycle**

1. Branch `<agent>/<task>` from current main (section "Branches").
2. Behaviour or interface changes: host regression for failure paths, updated
   mechanism description and migration notes ([API](API.md)), a CHANGELOG entry,
   a new spec revision. Code and tests refer to spec items per appendix D (`# ТЗ 5.9.7`).
3. Local checks of the affected levels (section "Checks").
4. Signed commit, push the branch, match check results to the branch's latest
   commit, merge into main.
5. Record the branch, commit and status in TODO.md.

**Release** (spec 8.9, [versioning rules](VERSIONING.md)):

1. `__version__` in `stm32_gdbtest/__init__.py`; `API_VERSION` and schema numbers
   change only when the corresponding contract changes.
2. A dated `## [X.Y.Z] - YYYY-MM-DD` section in the CHANGELOG (both languages);
   `[Unreleased]` stays for future changes.
3. A "release" spec revision with up-to-date appendices B and F.
4. Host and offline checks, consumer integration through a real submodule, agreed
   hardware and recovery checks on the final commit.
5. Merge into main, then an annotated signed tag `vX.Y.Z` on the merge commit with the
   message from `docs/releases/vX.Y.Z.md` ([tag and notes](VERSIONING.md#tag-and-release-notes)).
   Tags are never moved.

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
the checks the branch is merged into main by fast-forward and deleted with `git land` —
this order applies while one maintainer works with agents and is reconsidered when the team grows
([HOWTO](HOWTO.md#git-working-without-pull-requests)). A branch behind main is first
rebased onto it (`git rebase -S`, conflicts resolved, affected checks repeated). The owner may use `push --force-with-lease` for their own unmerged branch after rebase;
the new SHA needs fresh checks. Never rewrite main or another contributor's branch. Successful checks of an older commit do not count for new changes.
CI workflows run for any branch, so a new prefix needs no workflow change.

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
- The documentation map is [docs/en/index.md](index.md); a new page is added to both
  languages and both maps.
- Russian texts use the term «отладчик». The README is a short introduction (why,
  what, how, dependencies, links); exact results and limits go to STATUS, history
  to the CHANGELOG and protocols.


### Local development and public documentation

Research plans, prototypes and raw results remain local under `docs/research/`;
the entire directory is excluded from Git. Experimental test directories use the
`dev-*` prefix and the `tests/**/dev-*/` ignore filter. Existing experimental
directories and `tools/research/` are also explicitly excluded in .gitignore.
Do not force-add these files to the index.

Publish accepted contracts, techniques and acceptance results sufficient for users,
without links to local material. Production host tests, board fixtures and examples
remain public. In the release branch, run `python ci/run_checks.py docs`:
the separate docs.public check reads local-development filters from .gitignore and
rejects tracked private files and links into them, even if the target exists locally.
This governs the current tree; prior Git history is not automatically purged.

Before starting or continuing research, read the [dedicated agent rules](../../AGENTS.md#проведение-исследований)
and the local `docs/research/README.en.md`, if present, followed by the study plan, summary and latest
report. The local conventions define the `ru/en/results` structure and input/output filenames.
Result history is in local `docs/research/HISTORY.md` and `HISTORY.en.md`: date, brief change and
output links, newest first, without code versions. New studies use `plan.md`, `verification.md`, `results.md`, `questions.md` and
`technical-debt.md` in both languages; stages use `<stage>-plan.md` and `<stage>-results.md`.
Keep historical filenames and list them in the document map. Use lowercase-kebab-case directory names.
Record expected outcomes and conditions before runs; retain actual results, versions, prototype/input
hashes, logs and limitations afterwards. Never overwrite original FAIL/ERROR evidence after a fix.
Host PASS does not replace HW PASS; follow project hardware and restoration rules.
After each stage, update both report localizations, the summary, matrix, questions and local history;
tell the owner the result and next step. Distinguish observations, proposals and accepted decisions.
Report missing local materials explicitly rather than treating prior outcomes as verified.
Experimental API integration into the core requires separate agreement. Local paths here specify
storage conventions, not links to shipped documents; the publication checks above remain mandatory.

Section 2.1 of the local README defines the `tests/dev-*` sandbox: explicit run commands,
code-to-report links and preservation of tested source snapshots before editing.
Do not automatically include the sandbox in production tests, CI or the shipped package.

## Checks

1. Offline checks in the CI Docker image: `python3 ci/run_checks.py` — the docs, format, host
   and firmware levels ([checks and CI](testing.md)). Before a push run the levels
   affected by the change.
2. Module host tests without Docker: `python -B -m unittest discover -s tests/host -v`;
   debugger locking is tested by the tests of its OS (Windows or Linux). On a Linux
   stand run them after `. ~/.local/stm32-gdbtest/env.sh`; `python -B -m stm32_gdbtest doctor`
   checks the environment ([Linux stand](LINUX_STAND.md)).
3. Consumer example without a board (Windows): in `examples/minimal-consumer` —
   `cmake --preset debug`, `cmake --build --preset debug`, `ctest --preset offline`.
4. CLI: `python -B -m stm32_gdbtest --version`, `collect`, `trace`, `run --prepare-only`.
5. Specification: `check_spec.py --strict`.
6. Hardware checks only under the rules of "Working with hardware". The example's
   full `ctest` programs the MCU.

A build or host PASS is not a hardware PASS. A check report states the exact MCU,
HAL, GDB, backend, ELF and manifest, the effect of halt/reset and the limits of the
evidence. GitHub Actions CI (Docs and Offline workflows) checks the module up to
the GDB server; a result belongs to a specific commit and does not replace a
hardware check.

## Working with hardware

1. Before a hardware run, name the board, debugger, backend and connections;
   changing the stand requires the owner's confirmation. Do not infer wiring from
   USB enumeration.
2. Never enable mass erase, option bytes, debugger firmware updates, shared mode or
   Flash breakpoints automatically. After an experiment restore the agreed firmware
   and MCU state.
3. Do not run a third-party server on the same debugger in parallel. The lock only
   coordinates participating runners in one Windows session or on one Linux host;
   after a crash check
   for leftover GDB and server processes.
4. Do not hide ERROR or failure causes; do not rerun automatically to get a PASS.

## Module and consumer boundary

- The module is the infrastructure core. MCU, board, expectations, instruments and
  application tests belong to the consumer project. `tests/fixtures` are not working
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
- Files under `ci/**`, `.github/**` and `*.sh` are kept with LF in every working
  copy (`.gitattributes`): the CI image is also built on Windows. Other files in a
  Windows working copy may have CRLF (`core.autocrlf`) — keep the line endings of
  the file you edit.

## Dependent branch batches

By agreement with the owner, small tasks on one stand can be prepared in
batches of3–4 branches. Independent branches start at main; dependent branches
form a chain. Record bases/order in TODO. The owner pushes the batch; the agent
verifies each SHA and all CI before proposing sequential land. Old SHA checks
do not validate a rebase. Update the consumer gitlink after batch acceptance
unless an intermediate integration is needed for validation.

## Directory and local stand names

New owned directories use lowercase names. Profiles/examples use tests,
including profile/tests in newly written packages. Preserve third-party and
generated names such as Core. Existing external projects with Tests and schema1
packages with profile/Tests remain readable; uppercase compatibility fixtures
and the historical EXPORT_MANIFEST keep their spelling.

Local remote stands use remote.toml or <profile>-remote.toml, without .local.
Both patterns are ignored by Git; remote.example.toml remains a tracked template.
Rename existing files and update --stand/local presets. The loader does not
restrict TOML names, so old names still work. Reconfigure CMake after Tests →
tests: existing session.json files retain the old path. API_VERSION and package
schema are unchanged.
