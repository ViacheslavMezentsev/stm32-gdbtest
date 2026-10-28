# Release transitions

[Documentation](index.md) · [Русский](../ru/RELEASE_CHANGES.md)

A short user guide; full history is in [CHANGELOG](../../CHANGELOG.en.md).
Operational guides describe 0.6.x. DDTT and specification revisions are independent package versions.

| Transition | User-visible change | Action |
| --- | --- | --- |
| Early candidates → 0.3.0 | Navigation, watch, call/ret, tables, profile and records; renamed operations | Use API cards instead of old names; an in-memory journal is not an automatic file |
| 0.3.x → 0.4.0 | API 2, old names removed, records capture/export, SKIP, st-util and expanded schemas | Configure capture explicitly; distinguish scenario, capture and command outcome |
| 0.4.0 → 0.4.1 | Documentation, skills and DDTT; API 2 unchanged | Review development routes and evidence limits |
| 0.4.x → 0.5.0 | API 3, async navigation, wait/halt, bounded call, complete memory, single RHS, C++ preflight, MMIO/SVD, Renode/QEMU, inspect and DDTT qualification | Follow [migration](MIGRATION_050.md); move hidden calls into call and peripheral access into MMIO; repeat consumer acceptance |
| 0.5.0 → 0.5.1 (part of 0.6.0) | Updated docs, TECH-021–026 and a neutral state/queue example | API 3 retained; use the [example](../../tests/stateful-buffer/README.en.md); distinguish expected FAIL from infrastructure errors |
| 0.5.x → 0.6.0 | Journal/report quotas and policies (api schema 3), lossless result schema 2, C++ calls (this, signature, Pointer/Reference, non-virtual bases), input substitution examples, offline ROS1 bag import, `run --interactive` | API 3 retained; new features are opt-in — [moving to 0.6.0](VERSIONING.md#moving-to-060); repeat consumer acceptance |

Memory/write and C++ preflight plans were originally labelled "0.4.2"; they shipped in 0.5.0,
not in a separate released 0.4.2. Older write could evaluate a string RHS repeatedly; API 3
evaluates RHS once, requires stable LHS and forbids hidden calls. Old workarounds for unsized
char[] evaluate and outer quotes in reach are unnecessary; use the current
[evaluate](api/evaluate.md) and [reach](api/reach.md) cards.

## Historical material

Snapshots remain for reproducibility; their former "current" status does not apply to 0.6.x.

- [API.md](../archive/pre-050/en/API.md)
- [STATUS.md](../archive/pre-050/en/STATUS.md)
- [API_ACCEPTANCE.md](../archive/pre-050/en/API_ACCEPTANCE.md)
- [HARDWARE_METRICS.md](../archive/pre-050/en/HARDWARE_METRICS.md)
- [RUN_LAYOUTS.md](../archive/pre-050/en/RUN_LAYOUTS.md)
- [VERSIONING.md](../archive/pre-050/en/VERSIONING.md)
- [API030_PLAN.md](../archive/pre-050/en/API030_PLAN.md)
- [API040_SCENARIOS.md](../archive/pre-050/en/API040_SCENARIOS.md)
- [RC020_READINESS.md](../archive/pre-050/en/RC020_READINESS.md)
- [RC2_READINESS.md](../archive/pre-050/en/RC2_READINESS.md)
- [RELEASE040_SCOPE.md](../archive/pre-050/en/RELEASE040_SCOPE.md)
