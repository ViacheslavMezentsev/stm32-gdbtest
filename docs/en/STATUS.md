# Current status

[Documentation](index.md) · [Русский](../ru/STATUS.md)

Current version: **0.6.1 / API_VERSION=3** ([release notes](../releases/v0.6.1.md): diagnostics fixes and documentation order). The 0.6.x line provides long scenarios with journal quotas, C++ calls,
verified input substitution methods (simulated inputs — substituting data in memory or a function result), offline ROS1 bag import and an interactive scenario
walk-through in VS Code. The 0.5.1 preparation material is part of this release.

A8 acceptance at `6530395`: Windows/Linux, Renode/QEMU, six MCUs (including the new C++, journal
and substitution checks on real microcontrollers) and the BluePill/BlackPill consumers.
[Matrix and limits](../development/release-060-acceptance.md) (Russian),
[release notes](../releases/v0.6.0.md); previous: [0.5.0 acceptance](../development/release-050-acceptance.md),
[accepted results](../evidence/en/API_ACCEPTANCE.md). Evidence belongs to those revisions, not to every current stand.

Available: MMIO/SVD, inspect, synchronous and async scenarios, bounded call, live windows,
local/SSH stands, Renode/QEMU, records and DDTT export with condition qualification.
[API](API.md), [stands](STANDS.md), [live-window limits](LIVE_EXECUTION.md).

Next: [TODO](../../TODO.md), [ROADMAP](../../ROADMAP.md).
Stepping through a scenario: [run --interactive](MANUAL_DEBUG.md).
History and migration: [release transitions](RELEASE_CHANGES.md).
