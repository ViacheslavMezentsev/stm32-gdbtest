# Results and queue

[Research](index.md) · [Русский](../ru/results.md)

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
