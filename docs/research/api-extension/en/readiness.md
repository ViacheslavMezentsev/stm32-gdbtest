# First package: readiness matrix

[Research](index.md) · [Русский](../ru/readiness.md)

[TECH-010/011 hardware pairs on F030/F103/F411](techniques-three-boards.md): 7/7 HW and 7/7 prepare each; original checks preserved, restoration PASS. F103 Flash warning retained. Research facades, not core integration.

Owner decision 2026-10-03: numeric bounds/cost criterion and public RecordError import accepted. Q6/Q19 and API spec questions 10.2.4–10.2.5 closed; API spec 0.2.1, system spec 0.61. Upper-bound implementation and core integration are pending; integration approval remains separate.

Snapshot on 2026-10-03, after `5f7d749`. The first package is sufficiently researched
to discuss integration. Core integration and acceptance remain unperformed and
unauthorized. Normative sources: [API spec 0.2.0](../../../TECHNICAL_SPECIFICATION_API.md)
and [system spec 0.60](../../../TECHNICAL_SPECIFICATION.md). This report changes no
requirements and closes no questions without an owner decision.

## Contracts and evidence

“Prototype verified” means isolated implementation evidence. “Partial” identifies
remaining work in the last column. Production acceptance remains pending for every
row; historical PASS does not transfer to future code.

| Area | Traceability | Status / evidence | Remaining work |
| --- | --- | --- | --- |
| Scope and versions | Q16; API 3.3, 7.1–7.5; system 8.48; A1 | Accepted: record/records, RecordError, config/config_props, session.toml; spec 0.2.0, module target 0.2.0, API_VERSION=1, schema=1; [M5](m5-contract.md) | Exact prerelease before release; separate integration approval |
| Copies, ordering, types, filters | J1–J6/J11; API 4.9.1–4.9.3, 4.10; TC-06/07; A2 | Prototype verified: [E1](e1.md), [errors](record-errors.md) | Repeat against production Target |
| Ownership and lifetime | J7–J10; API 4.9.4–4.9.5; TC-08; A3 | Partial: facade isolation, Python-only operations, no export | Two real case invocations, clear/resume/reset, agent exit/error handling |
| Errors | Q18; API 5.3–5.4; TC-07/12; A4 | Prototype verified: all code/limit values, atomicity, injected MemoryError; [18/18 in two GDB builds](record-errors.md) | Public import/base class, integrated ERROR/FAIL and early missing-API diagnostics |
| Limits and costs | Q6/Q19; J12; API 6.3–6.5; TC-11; A5 | Partial: [13 shapes/5 boundaries in three environments](records-cost.md) | Approve numbers/criteria; enforce upper bounds, remeasure integrated code |
| TOML loading and views | Q20; API 4.11–4.12; TC-09; system 5.20.2–5.20.7 | Prototype verified: [M2/M3](config-loader.md), defaults/unknown/read-only/hashes | Bind one snapshot to production prepare/agent without rereading originals |
| CMake/JSON and conflicts | System 5.20.1/4/5; TC-148 | Partial: [M4](config-transport.md), old/new/conflict configure | Production SESSION_CONFIG, CTest/CLI, legacy paths and invalid/missing without fallback |
| TOML transport and defaults | System 5.20.8–5.20.9; TC-149 | Prototype verified: [transport](config-transport.md), TOML types, hashes, defaults mismatch | Internal envelope version/comparison algorithm; production agent and receiver-host execution |
| Prepare/pack/open | System 5.20.6/11/12; TC-149/150 | Partial: [pipeline](config-pipeline.md), real F030 ELF prepare, production ZIP, GDB facade 6/6 | Production --package/CTest; legacy/new transfer without original paths |
| Legacy config/config_props | System 5.20.10–5.20.11; TC-150 | Prototype verified: [old JSON/packages](legacy-config.md), 6/6 in two GDB builds | Bind views to actual runner snapshot; package test ELF is synthetic |
| Compatibility and boards | API TC-12; system TC-151; A6 | Partial: [F0/F1](portability.md), [F411](e1-comparison.md), historical research results | Full core host regression and paired old/new scenarios on F030/F103/F411, baseline/restore |

TC-06…TC-12 belong to the API spec; TC-148…TC-151 to the system spec.
J/A are local identifiers from [E6](e6-proposal.md).

Latest full prototype regression: Linux 79/79; Windows 78 PASS and 1 CMake skip.
GDB suites 18/18 (journal) and 6/6 (legacy) are not additional unique tests:
they repeat corresponding host checks in another environment. No hardware runs
occurred in the latest stages.

## Remaining first-package decisions

| Decision | Recommendation | Status |
| --- | --- | --- |
| Q6/Q19, API 10.2.4 | defaults/max: records 128/1024, nodes 4096/32768, text_bytes 65536/524288, depth 8/32, integer_bits 256/1024 | Approved 2026-10-03 |
| Cost criterion | Repeat suite during integration; investigate >2x median regression in comparable environments; no RSS/latency guarantee | Approved 2026-10-03 |
| API 10.2.5 | `from stm32_gdbtest import RecordError`; subclass ValueError, importable without GDB | Approved 2026-10-03 |
| Integration | Accepted first package only, as a separate stage with documentation and regression | Not authorized |

Root-package import avoids scenario dependencies on internal modules. The exception
needs no GDB, preserving host testing. ValueError fits invalid-input failures and
is already used by the prototype; precise handling uses RecordError.code/limit.

Proposed public use, not available in the rc.2 core yet:

```python
from stm32_gdbtest import RecordError

try:
    t.record('sample', measurement)
except RecordError as error:
    if error.code == 'limit_exceeded':
        raise RuntimeError(f'record budget exceeded: {error.limit}') from error
    raise
```

This is explicit scenario policy: it neither hides an incomplete measurement series
nor attempts another write into an already full journal.

General future breaking-change policy (API 10.2.2) remains open, while this particular
compatible addition and its versions are accepted. Q3–Q5 and Q7–Q15 primarily concern
deferred read/context/caller/finish work; they stay open and outside automatic scope.
Preserving primary errors during integration is checked separately from the broader
future cleanup model Q13.

## Order after decisions

1. Record approved numbers/import in a new API spec revision and refresh its
   discrepancy table using later evidence. Retain historical reports.
2. After separate integration approval, implement the first package: shared config
   snapshot, transport/validation, Target/errors, CMake/CLI/legacy.
3. Run positive/negative integration checks from this matrix, existing-scenario
   regression, paired agreed-board comparisons and repeated cost measurements.
4. Produce acceptance report; exact prerelease, merge and publication are separate steps.

Next discussion: two contract decisions—numeric bounds/criterion and public import/
base class. Their acceptance alone does not authorize core integration.

## Scenario adaptation: before and after integration

Proposed sequence (next-stage explanation, not integration authorization):

1. **Before core integration:** enforce accepted bounds in the isolated configuration;
   choose 2–3 representative scenarios (VDDA/temperature series, HAL/ADC with several
   observations, configurable scenario). Build paired facade variants, retaining
   original controls and reusing earlier E1 variants. Preserve assertions and coverage.
2. Verify configuration/prepare, then paired runs on an agreed stand. Compare check
   semantics and outcomes, not identical temperatures across runs. Mark hardware
   unverified if the stand is unavailable.
3. **After separate authorization:** integrate the API and replace the facade with
   real Target in experimental scenarios. Repeat host/prepare and hardware acceptance,
   including baseline/restore and negative outcomes.
4. **After acceptance:** adapt remaining suitable scenarios where records/config add
   value. Simple checks can retain value/check; rewriting every scenario is unnecessary.

Next practical step: enforce and test approved prototype upper bounds, then select
and prepare paired scenarios. This evaluates usability before integration and
verifies actual core compatibility afterward.
