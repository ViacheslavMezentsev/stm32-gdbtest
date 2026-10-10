# Proposed v0.4.0 scope

[Documentation](index.md) · [Русский](../ru/RELEASE040_SCOPE.md) · [Release policy](VERSIONING.md) · [Roadmap](../../TODO.md)

Scope agreed on 2026-10-09 and reconciled with `main` at `44c795d`: `codex/check-techniques`,
`codex/api040-cleanup`, and `codex/api030-feedback` have landed. This defines the release boundary,
not release readiness. At this snapshot the module is version 0.3.0 with `API_VERSION=2`;
the release branch raises the Python version to 0.4.0. Final acceptance remains.

## 1. Recommended contents

| Group | v0.4.0 decision | Evidence and gate |
| --- | --- | --- |
| Journal/results | Include opt-in `records.json` capture, `results export/verify`, campaign index and standalone JSON/HTML report with themes and normal/expert controls | Already implemented in `[Unreleased]`; verify them together at the release SHA, including capture failure |
| `skip(reason)` | Include minimal imperative SKIP, code 77, JUnit/CTest and explicit `run_hw` allowance | Host/docs and hardware studies completed; retain the [method limits](api/skip.md) |
| `reach` correction | Include GDB single-quoted C++ signature handling | Host/hardware regression exists; repeat at the release SHA |
| Compatible MCUs/infrastructure | Include AT32 profile, stand naming and architecture adapters | Already in `[Unreleased]`; verify available backend/build paths at the release SHA |
| Techniques/examples | Include event/interval, watchpoint wait, injection, standalone C++ Og/O2 and TECH-019 | Examples built on existing API, without new `Target` methods |
| 0.3.0 field feedback F01–F03 | Include; `codex/api030-feedback` has landed | F01 bounded unsized character-array read; F02 watchpoint frame interpretation; F03 initial SP as SRAM boundary. Host/docs/offline passed at `44c795d`; hardware results predate integration and need a release-SHA repeat |
| API cleanup | **Remove** `value`, `fields`, `set_value`, `force_return` | API spec 6.7, TODO and reference have promised removal in 0.4.0; provide explicit migration for this breaking change |
| st-util | Include a separate backend and optional `[st-util]` target schema 2 section | Agreed on 2026-10-10. Five STM32/Windows lifecycles and full suites passed; OrangePi/SSH hardware remains unverified. [Matrix](API_ACCEPTANCE.md) |

`API_VERSION` is already 2 because public methods were removed. The release branch raises
the target.toml schema to 2 for backend dialects; other TOML/JSON schemas remain unchanged.
Keep `@case` as primary and `@test` as an alias: neither is deprecated.

## 2. Scenario and documentation cleanup

A scan of *Git-tracked files* for `t.<name>(…)` and `target.<name>(…)` found:

| Location | Finding | Action |
| --- | --- | --- |
| `tests/firmware/common/tests`, `tests/firmware/profiles` | No calls of the four former methods | Repeat stock scenarios at the release SHA |
| `tests/host` | Absence checks for former names and current `ret`/`write` regressions are in main | Repeat host regression at the release SHA |
| `docs/ru`, `docs/en` | Active examples use the current API; former names remain in historical migration | Check `docs.public` and language pairs at the release SHA |
| `skills/stm32-gdbtest-scenarios` | Old-to-new table remains only as migration guidance | Working examples use the current API |
| Local `tests/dev-*` and historical results | Earlier research code calls old names | Preserve historical evidence; do not distribute these directories |

Do not blindly replace text:

- `value(expr)` returned `int`: use `read(path)` for an object, `evaluate(expr)` for a C/GDB expression, checking the desired type.
- `fields(expr, expected)` performed ordered comparisons and evaluated string expectations. `check(rows)` must preserve order, names and expression evaluation; `read(..., fields=…)` only reads fields.
- `set_value` returned `None`; `write` returns a result and verifies the applied write. Review any scenario relying on return values or MMIO read effects.
- `force_return` becomes `ret`; verify returned details and expression type in the current frame.

The cleanup branch resolved the old cards' contradictory warning/alias text. Specification and CHANGELOG
history is preserved. A tracked-file scan at `44c795d` finds calls of former names only in the skill's
migration table; these are examples of old code, not executable scenarios.

## 3. Exclude from v0.4.0

| Candidate | Why defer |
| --- | --- |
| GDB bit functions, `bits`, `each`, `predicate` | Prototypes were studied; zero-mask, empty-array, limits, diagnostics and side-effect semantics still need decisions. Separate package after scope review |
| SVD tools and T6, comparative T7 summary | T6 is not completed; this research does not gate the already implemented package |
| `requires`, dependency tree, automatic group skips | Dynamic facts/lifecycle need separate contracts; minimal `skip(reason)` works now |
| `fault`, `cycles`, `snapshot/diff`, HSE measurement | Open TODO/API-spec candidates without agreed implementation and acceptance for v0.4.0 |
| RTOS awareness and external equipment | Separate research and integration |

## 4. Technical debt and release gates

The 2026-10-10 recheck updates acceptance: [current matrix](API_ACCEPTANCE.md).
Docker 26/26 and six OpenOCD/J-Link boards passed; full F411/F030 ST-LINK suites remain
open due to USB ERROR. The historical table below does not override these results.

- Use `skip()` in consumer scenarios to learn where it is needed; distinguish inapplicability from malfunction. Direct GDB is unrestricted and SKIP does not roll back actions. This package has not rechecked remote stands or other GDB versions.
- F01–F03 are integrated: TECH-013 explains why a stop frame need not identify the writer, and TECH-017
  separates the initial SP at a RAM boundary from readable addresses. Earlier hardware evidence does not
  replace a run at the release SHA.
- Release matrix: Docker host/offline/docs at the exact SHA, real build/package, [release-policy](VERSIONING.md) launch schemes, hardware recovery, a consumer using the actual submodule, and `docs.public`. Branch-local results do not replace final-SHA CI.
- Align version, `API_VERSION`, current revisions of both specifications, README/STATUS, skills, bilingual CHANGELOG and release notes. Provide a 0.3.0 migration guide.

| Evidence | At `44c795d` | Release gate |
| --- | --- | --- |
| Docs, host, F030 offline | 7/7 passed locally | Repeat full Docker suite and GitHub CI at the final SHA |
| Board scenarios and recovery | At `bb74cde`, six local stands: 10/10 `run_hw` each, 280 scenarios, 608 stages (602 PASS, 6 expected ERROR), BOOT/GPIO recovery 12/12 PASS | Other [release-policy](VERSIONING.md) layouts, affected `run_hw` repeat at the final SHA, and CI |
| Consumer as Git submodule | Untested at the integrated SHA | Verify real gitlink and prepare/run path |
| Version and release documents | `__version__=0.3.0`, API_VERSION=2 | Version 0.4.0, specifications, migration and release notes |

## 5. Release preparation sequence

1. Reconcile the integrated scope and verification matrix: `main` at `44c795d` includes all three accepted
   branches. Docs 5/5, host and F030 offline passed locally on this SHA (7/7 total); the owner checks GitHub CI separately.
2. In the release branch, `__version__` is set to 0.4.0 and both specifications, README/STATUS, skills,
   bilingual CHANGELOG and draft release notes include 0.3.0 → 0.4.0 migration.
   `API_VERSION=2` is already set; documents will be refined after final acceptance.
3. At `bb74cde`, all six local stands passed their scenarios and recovery. At the final SHA, run Docker
   docs/format/host/firmware, repeat the affected `run_hw` path and remaining layouts, then check a
   consumer with the real submodule. Record exact tool versions, MCU, backend, ELF/manifest and limits;
   do not count results from earlier SHAs as final acceptance.
4. The owner pushes the branch, checks CI at the last SHA, lands it, then creates the tag.

This scope does not transfer experimental methods into core or publish a release.
