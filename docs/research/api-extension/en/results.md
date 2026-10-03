# Results and queue

[Research](index.md) · [Русский](../ru/results.md)

[Production scenario migration](scenario-migration.md): five CMSIS profiles 103/103, HAL F030 22/22, minimal consumer 1/1; recovery and restoration counted separately. Core unchanged, version 0.2.0.dev0. Next: version preparation review; historical evidence follows.

[First-package integration](core-integration.md) authorized and implemented: Target, session.toml, snapshot/package; 7/7 HW on each of three stands. Development 0.2.0.dev0; release separate. Material below preserves earlier stages.

As of 2026-10-03, E1 prototype host checks passed: 22/22.
[E1 report](e1.md), [registry](../results/registry.json).
GDB/F411: 10 observations, baseline/experiment/restore 4/4 PASS; two corrected
preparation errors before connection are retained. Documentation checks are separate.

| Stage | Status | Next deliverable |
| --- | --- | --- |
| E1 — record | Complete: host 22/22, both F411 hardware series 4/4 PASS each | [Conclusions and limitations](e1-comparison.md) |
| E2 — read | Bounded prototype: host 29/29, HW F411 4/4 PASS | [Report and open questions](e2.md), next E3 |
| E3 — frames/context | Host 36/36; HW ERROR → correction → 4/4 PASS, both restores PASS | [Report](e3.md); next E4 |
| E4 — finish | Bounded experiment: host 44/44; HW ERROR → correction → 4/4 PASS | [Report and full-acceptance debt](e4.md); next E5 |
| E5 — conventions review | Review complete; accepting the whole package is not recommended | [Matrix, gaps and recommendations](e5.md) |
| E6 — acceptance and migration | Awaiting owner review of E5 and approval | Versioning, Q1–Q16 decisions, API acceptance and revised scenarios |

After each stage, update this table, add a separate report and name the next step.
Do not import hardware outcomes from the first study as new results.

[E1–E4 continuation on F0/F1](portability.md): 8/8 HW per board, limitations and retained prepare ERROR. [API spec 0.1.0](../../../TECHNICAL_SPECIFICATION_API.md) captures current rc.2 without integrating extensions. Next: Q1–Q16 review and E6 approval.

[E6: proposed first package](e6-proposal.md) — record/records contracts, Q1–Q16 recommendations, versions and acceptance. New Q17–Q19 are appended to the queue; core integration is not approved.

[M2/M3: host configuration prototype](config-loader.md) — 12 new tests, Windows 56/56 including E1–E4, initial CRLF test-expectation FAIL retained. Next M4; core unchanged.

[M4: transport and CMake](config-transport.md) — Linux 64/64, Windows 63 PASS/1 skip; JSON/config-ZIP, actual old/new/conflict configure, legacy prepare PASS. M4 partial: production package/agent not integrated.

[M4: end-to-end pipeline](config-pipeline.md) — real F030 ELF prepare PASS, production package, GDB-Python 6/6 without MCU; Linux 68/68, Windows 67 PASS/1 skip. Next: remaining contract decisions before M5.
