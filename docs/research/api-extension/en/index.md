# API extension research using existing scenarios

[Documentation](../../../en/index.md) · [Русский](../ru/index.md)

[Production scenario migration](scenario-migration.md): five CMSIS profiles 103/103, HAL F030 22/22, minimal consumer 1/1; recovery and restoration counted separately. Core unchanged, version 0.2.0.dev0. Next: version preparation review; historical evidence follows.

[First-package integration](core-integration.md) authorized and implemented: Target, session.toml, snapshot/package; 7/7 HW on each of three stands. Development 0.2.0.dev0; release separate. Material below preserves earlier stages.

[Records bounds](config-bounds.md): implemented in the prototype; Linux 91/91 PASS, Windows 90 PASS/1 skip. Next: discuss first-package integration.

[TECH-010/011 hardware pairs on F030/F103/F411](techniques-three-boards.md): 7/7 HW and 7/7 prepare each; original checks preserved, restoration PASS. F103 Flash warning retained. Research facades, not core integration.

[First-package readiness matrix](readiness.md) — current contracts, evidence and remaining decisions; integration not authorized.

[M5: accepted first-package contract](m5-contract.md) — API spec 0.2.0, system spec 0.60; rc.2 core, separate integration approval.

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

[E1–E4 continuation on F0/F1](portability.md): 8/8 HW per board, limitations and retained prepare ERROR. [API spec 0.1.0](../../../TECHNICAL_SPECIFICATION_API.md) captures current rc.2 without integrating extensions. Next: Q1–Q16 review and E6 approval.

[E6: proposed first package](e6-proposal.md) — record/records contracts, Q1–Q16 recommendations, versions and acceptance. New Q17–Q19 are appended to the queue; core integration is not approved.

[Q20: session.toml migration plan](session-migration.md) — CMake/CLI, shared snapshots, conflicts, compatibility and M1–M6 checks. Proposal only, not core integration approval.

[M2/M3: host configuration prototype](config-loader.md) — 12 new tests, Windows 56/56 including E1–E4, initial CRLF test-expectation FAIL retained. Next M4; core unchanged.

[M4: transport and CMake](config-transport.md) — Linux 64/64, Windows 63 PASS/1 skip; JSON/config-ZIP, actual old/new/conflict configure, legacy prepare PASS. M4 partial: production package/agent not integrated.

[M4: end-to-end pipeline](config-pipeline.md) — real F030 ELF prepare PASS, production package, GDB-Python 6/6 without MCU; Linux 68/68, Windows 67 PASS/1 skip. Next: remaining contract decisions before M5.

[Q6/Q19: journal time and memory](records-cost.md) — 13 input shapes and 5 boundaries in CPython/GDB14/GDB16; proposed limits await approval.

[RecordError: structured rejection](record-errors.md) — prototype code/limit implemented, GDB14/GDB16 18/18 PASS each; next legacy config/config_props.

[Legacy config/config_props](legacy-config.md) — old JSON/packages, image precedence, capture and immutability; GDB14/GDB16 6/6 each. Next: consolidated readiness matrix.

[TECH-010: table-driven checks](table-checks.md) — 47 candidate blocks, 82 paired cases; technique over rc.2, no new API/HW.

[TECH-011: acquisition and calculation](measurement-technique.md) — configured VDDA/temperature pair, Python mean/deviation and GDB arithmetic on captured values; no new HW runs.
