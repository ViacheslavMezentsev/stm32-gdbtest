# Proposed v0.4.0 scope

[Documentation](index.md) · [Русский](../ru/RELEASE040_SCOPE.md) · [Release policy](VERSIONING.md) · [Roadmap](../../TODO.md)

Scope agreed on 2026-10-09 and reconciled with `main` at `44c795d`: `codex/check-techniques`,
`codex/api040-cleanup`, and `codex/api030-feedback` have landed. This defines the release boundary,
not release readiness. Current state was reconciled on 2026-10-10 against `a6b6dbd`;
stm32-gdbtest 0.4.0, `API_VERSION=2`. The local matrix below does not replace latest-SHA CI.

## 1. Recommended contents

| Group | v0.4.0 decision | Evidence and gate |
| --- | --- | --- |
| Journal/results | Include opt-in `records.json` capture, `results export/verify`, campaign index and standalone JSON/HTML report with themes and normal/expert controls | Already implemented in `[0.4.0]`; verify them together at the release SHA, including capture failure |
| `skip(reason)` | Include minimal imperative SKIP, code 77, JUnit/CTest and explicit `run_hw` allowance | Host/docs and hardware studies completed; retain the [method limits](api/skip.md) |
| `reach` correction | Include GDB single-quoted C++ signature handling | Host/hardware regression exists; repeat at the release SHA |
| Compatible MCUs/infrastructure | Include AT32 profile, stand naming and architecture adapters | Already in `[0.4.0]`; verify available backend/build paths at the release SHA |
| Techniques/examples | Include event/interval, watchpoint wait, injection, standalone C++ Og/O2 and TECH-019 | Examples built on existing API, without new `Target` methods |
| 0.3.0 field feedback F01–F03 | Include; `codex/api030-feedback` has landed | F01 bounded unsized character-array read; F02 watchpoint frame interpretation; F03 initial SP as SRAM boundary. Host/docs/offline passed at `44c795d`; hardware results predate integration and need a release-SHA repeat |
| API cleanup | **Remove** `value`, `fields`, `set_value`, `force_return` | API spec 6.7, TODO and reference have promised removal in 0.4.0; provide explicit migration for this breaking change |
| st-util | Include a separate backend and optional `[st-util]` target schema 2 section | Agreed on 2026-10-10. Five STM32/Windows lifecycles and full suites passed; OrangePi/SSH full suites on five STM32 boards also passed. [Matrix](API_ACCEPTANCE.md) |

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

## 4. Evidence and open limits

stm32-gdbtest 0.4.0, API_VERSION=2, target schema 2; general specification 0.94, API specification 0.3.16.
The release is being prepared in `codex/release-040` and is not published.

Local evidence belongs to several revisions:

- `b1264c1`: Docker 26/26; six Windows OpenOCD/J-Link stands, 280 scenarios,
  608 stages; Linux-built F411/F429 packages on Windows 10/10 each; minimal-consumer
  with a real submodule passed offline 3/3 and GPIO on F411.
- Remote lifecycle `4cb5e0a`, scenarios through `a6b6dbd`: Windows → OrangePi/st-util 1.9.0,
  five STM32 boards, 233 scenarios, 516 stages including prepare and restoration;
  268 HW PASS and 5 expected timeout ERROR outcomes, OpenOCD BOOT/GPIO 10/10 and clean release.
  F4 ADC_INVALID received 120s after the preserved F411 ERROR; changed F401 was checked separately.
- After lifecycle changes: 426 host tests, Docker docs+host 6/6; final documents are checked separately.

Full F411/F030 ST-LINK GDB Server suites remain unaccepted because of USB ERROR.
Passing st-util does not close this failure. USB serial diagnostics in doctor, the cause of the
previous F429 SP/SRAM anomaly and forced-cleanup limits remain open as well.
Latest-SHA GitHub CI and final reconciliation of all release layouts remain pending.

Historical protocols and exact boundaries: [matrix](API_ACCEPTANCE.md).

| Remaining item | Status and next action |
| --- | --- |
| F411/F030 ST-LINK GDB Server | Boundary approved on 2026-10-10; USB ERROR remains open debt 11.2.27 |
| Latest SHA | Check Docker/offline and GitHub CI; runtime changes require affected layouts and recovery checks |
| Deployment layouts and consumer | Earlier evidence is retained; reconcile subsequent helper changes with local Linux, WSL, packages and Hardware CI instead of carrying PASS forward automatically |
| Doctor/USB serial | Empty or binary serial; Windows capture needs UTF-8, see HOWTO; representation fix is not accepted yet |
| F429 SP/SRAM | Not reproduced in the repeated campaign; cause unknown |
| Forced termination | Host regression exists; SSH loss on real USB and emergency cleanup safety are not established |
| Deferred checks | Hardware HAL F030, occupied-port retry, consumer SKIP practice; other API debt is in section 3 |

## 5. Completing preparation

1. Reconcile the final diff with tested sources, schemas and migration; test new changes according to impact.
2. Finish remaining release checks and record the exact SHA; retain the approved ST-LINK limitation.
3. The owner pushes the branch, verifies latest-SHA CI and lands it.
4. Only after acceptance: date the CHANGELOG, create the signed tag and publish as owner.

This scope does not declare the release ready or transfer experimental methods into core.

External finite package dispatcher: [stand_loop](STAND_LOOP.md). Target API and existing run/pack commands are unchanged.

## Owner decision — 2026-10-10

Release with the known F411/F030/ST-LINK GDB Server limitation is approved; USB ERROR
remains open technical debt 11.2.27. Verified alternatives are OpenOCD/st-util.

- Selected API 0.4.0 scenarios: GitHub Hardware at `c23f8fe`, WSL2 → OrangePi at
  `d1a9361`, and Windows/st-util at `c156db5`: each has 20 PASS + 5 expected SKIP on five
  STM32 boards; records, export and reports verified. These are distinct revisions, not latest-SHA CI.
- `stand_loop` on F411/OrangePi: two cycles (2 PASS + 2 SKIP), STOP and rejection of
  unexpected SKIP. The systemd service and pi/Qwen agent have not been exercised.
- Latest host regression after stand_loop: 451 tests, 4 expected skips; Docker docs+host
  6/6. TOML comments do not change active settings.

## Final release handoff

GitHub Docs, Offline and Hardware #14 succeeded at `ba10b12`. Subsequent changes
are documentation only; tested code and configuration are unchanged.
The local AT32/Windows run additionally completed the selected sixth-board matrix.
v0.4.0 content preparation is complete; final documentation push, CI of that SHA,
land and the signed tag remain with the owner. Known limitations above still apply.
