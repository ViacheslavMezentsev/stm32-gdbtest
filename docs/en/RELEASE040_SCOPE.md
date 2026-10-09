# Proposed v0.4.0 scope

[Documentation](index.md) · [Русский](../ru/RELEASE040_SCOPE.md) · [Release policy](VERSIONING.md) · [Roadmap](../../TODO.md)

Snapshot of `codex/check-techniques` at `00d8c18`, 2026-10-09. This is a proposed release boundary, not a release-readiness claim. The module is still version 0.3.0; the branch has not landed in main. The owner publishes after final CI and acceptance.

## 1. Recommended contents

| Group | v0.4.0 decision | Evidence and gate |
| --- | --- | --- |
| Journal/results | Include opt-in `records.json` capture, `results export/verify`, campaign index and standalone JSON/HTML report with themes and normal/expert controls | Already implemented in `[Unreleased]`; verify them together at the release SHA, including capture failure |
| `skip(reason)` | Include minimal imperative SKIP, code 77, JUnit/CTest and explicit `run_hw` allowance | Host/docs and hardware studies completed; retain the [method limits](api/skip.md) |
| `reach` correction | Include GDB single-quoted C++ signature handling | Host/hardware regression exists; repeat at the release SHA |
| Compatible MCUs/infrastructure | Include AT32 profile, stand naming and architecture adapters | Already in `[Unreleased]`; verify available backend/build paths at the release SHA |
| Techniques/examples | Include event/interval, watchpoint wait, injection, standalone C++ Og/O2 and TECH-019 | Examples built on existing API, without new `Target` methods |
| 0.3.0 field feedback F01–F03 | Candidate after separate push/CI/land of `codex/api030-feedback` and renewed compatibility review | F01 bounded unsized character-array read; F02 watchpoint frame interpretation; F03 initial SP as SRAM boundary. This branch also edits `target.py`, documentation and host tests; it is not in main/current branch |
| API cleanup | **Remove** `value`, `fields`, `set_value`, `force_return` | API spec 6.7, TODO and reference have promised removal in 0.4.0; provide explicit migration for this breaking change |

`API_VERSION` is currently 1. Public method removal changes the contract; recommend 2 in the release branch. TOML/JSON schema versions remain unless their formats change. Keep `@case` as primary and `@test` as an alias: neither is deprecated.

## 2. Scenario and documentation cleanup

A scan of *Git-tracked files* for `t.<name>(…)` and `target.<name>(…)` found:

| Location | Finding | Action |
| --- | --- | --- |
| `tests/firmware/common/tests`, `tests/firmware/profiles` | No calls of the four former methods | Scan again after branch integration; run stock scenarios on the release SHA |
| `tests/host` | Compatibility tests for `force_return`/`set_value` and warnings | Replace with absence checks and current `ret`/`write` regressions; retain existing behavioral coverage |
| `docs/ru`, `docs/en` | Active examples in API, DDTT and `case`, `check-failed`, `record` cards; separate cards of all four former names | Use `read`/`evaluate`, `check(rows)`, `write`, `ret`; keep former-name cards as historical migration and remove them from active method listings |
| `skills/stm32-gdbtest-scenarios` | Old-to-new table | Keep only as explicit migration guidance; working examples use current API |
| Local `tests/dev-*` and historical results | Earlier research code calls old names | Preserve historical evidence; do not distribute these directories |

Do not blindly replace text:

- `value(expr)` returned `int`: use `read(path)` for an object, `evaluate(expr)` for a C/GDB expression, checking the desired type.
- `fields(expr, expected)` performed ordered comparisons and evaluated string expectations. `check(rows)` must preserve order, names and expression evaluation; `read(..., fields=…)` only reads fields.
- `set_value` returned `None`; `write` returns a result and verifies the applied write. Review any scenario relying on return values or MMIO read effects.
- `force_return` becomes `ret`; verify returned details and expression type in the current frame.

Legacy cards currently say both “deprecated warning” and “alias without warning until 1.0”; fix this contradiction. Preserve version history in specifications and CHANGELOG. Active reference and examples must describe v0.4.0. After cleanup, old names should appear in tracked scenarios and active examples only within explicitly historical migration sections.

## 3. Exclude from v0.4.0

| Candidate | Why defer |
| --- | --- |
| GDB bit functions, `bits`, `each`, `predicate` | Prototypes were studied; zero-mask, empty-array, limits, diagnostics and side-effect semantics still need decisions. Separate package after scope review |
| SVD tools and T6, comparative T7 summary | T6 is not completed; this research does not gate the already implemented package |
| `requires`, dependency tree, automatic group skips | Dynamic facts/lifecycle need separate contracts; minimal `skip(reason)` works now |
| `fault`, `cycles`, `snapshot/diff`, HSE measurement | Open TODO/API-spec candidates without agreed implementation and acceptance for v0.4.0 |
| RTOS awareness and external equipment | Separate research and integration |

## 4. Technical debt and release gates

- Use `skip()` in consumer scenarios to learn where it is needed; distinguish inapplicability from malfunction. Direct GDB is unrestricted and SKIP does not roll back actions. This package has not rechecked remote stands or other GDB versions.
- F01–F03 need branch reconciliation and affected tests; until then they are **not** guaranteed v0.4.0 contents.
- TODO TECH-016/017: clarify writer frames and initial-SP/RAM boundaries in the techniques catalog if F02/F03 land.
- Release matrix: Docker host/offline/docs at the exact SHA, real build/package, [release-policy](VERSIONING.md) launch schemes, hardware recovery, a consumer using the actual submodule, and `docs.public`. Branch-local results do not replace final-SHA CI.
- Align version, `API_VERSION`, current revisions of both specifications, README/STATUS, skills, bilingual CHANGELOG and release notes. Provide a 0.3.0 migration guide.

## 5. Sequence before the release branch

1. Owner pushes `codex/check-techniques`, reviews last-SHA CI and lands it.
2. Reconcile and finish `codex/api030-feedback` separately under the same workflow. If incompatible or unfinished, leave F01–F03 outside v0.4.0.
3. From current main, create a small cleanup branch for four methods and migration of tracked tests/examples; verify host, docs, firmware prepare and affected hardware behavior.
4. Once scope is fixed, prepare a release branch: 0.4.0 version, `API_VERSION=2` if removal is accepted, specifications, CHANGELOG, release notes and final matrix. Owner handles push, land and tag.

This scope does not transfer experimental methods into core or publish a release.
