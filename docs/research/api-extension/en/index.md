# API extension research using existing scenarios

[Documentation](../../../en/index.md) · [Русский](../ru/index.md)

Started on 2026-10-03 in `codex/api-extension-research`, based on main
`b3d19e08de7553f0f9d21c92cf5f8750d836d80d`. At branch creation, GitHub main was
checked through the GitHub API and matched the local base.

The goal is to evaluate a small API extension against v0.1.0-rc.2 using existing
board scenarios: reduce scaffolding while preserving checks and improving diagnostics.
This separate study continues [GDB Python R1–R18](../../rc3-gdb-python/en/index.md).
Historical reports from that study remain unchanged.

- [Plan and candidates](plan.md).
- [Results and queue](results.md).
- [E1: runtime journal and VDDA/temperature statistics](e1.md).
- [E1: paired comparison and conclusions](e1-comparison.md).
- [E2: bounded typed reads](e2.md).
- [E3: stack and minimal context](e3.md).
- [E4: natural return and foreign stops](e4.md).
- [E5: conventions conformance and acceptance readiness](e5.md).
- [Machine-readable run registry](../results/registry.json).
- Contract foundations: [API proposal](../../rc3-gdb-python/en/api-proposal.md) and
  [evolution conventions](../../rc3-gdb-python/en/api-evolution.md).

Research prototypes may be developed in a separate experiment namespace.
Promotion into `stm32_gdbtest`, public API changes, API_VERSION changes and normative
specification changes require a separate decision. Creating this branch does not
approve the draft conventions. Hardware stages and RTOS work from the first study
remain paused; new hardware runs require separate planning and a confirmed current bench.
