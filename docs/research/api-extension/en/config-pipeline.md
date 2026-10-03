# M4: end-to-end prepare → package → GDB scenario

[Study](index.md) · [Русский](../ru/config-pipeline.md)

2026-10-03, continues [M4 transport](config-transport.md), baseline 2448284.
[Pipeline](../../../../tests/api-extension/session_pipeline.py),
[reproducible run](../../../../tests/api-extension/run_config_pipeline.py),
[host tests](../../../../tests/api-extension/test_session_pipeline.py).
Core/firmware unchanged; no MCU connections.

## Real local experiment

1. Captured session/target/api/image for the existing F030 ELF. API supplies
   max_records=7 and unknown measurement section with samples=3 and a TOML date.
2. Pipeline freezes ELF, manifest, scenarios and captured target in a temporary
   project and validates manifest against ELF and exact target bytes.
3. Production runner prepares HW_CI_ADC_UNITS with prepare_only=True and captured
   full-image policy. PASS: ELF contract, image and carrier checks without MCU.
   Logs are retained before the temporary project is removed.
4. Production pack creates schema-1 ddtt-package with ELF/manifest/scenarios plus
   research/config.json via existing include support. The original TOML directory
   is moved, invalidating old references.
5. Production open_package verifies hashes and restores the package. Research
   open_configured restores the snapshot, matches its target against the packaged
   profile and revalidates the manifest. GDB cwd is the receiver directory.
6. Real GDB-Python creates real Target without boot/connect. ConfiguredTarget
   exposes read-only properties and delegates check. Six checks PASS: profile MCU,
   consumer value, date type, no defaults in props.data, defaults in config, and
   Journal using configured limits. Target.close removes the stop handler.

This verifies infrastructure with real ELF/GDB, not running firmware. No target
remote/continue commands; connection_attempted=false. The GDB scenario is a research
smoke-script, not a board case through production agent. Journal is explicit;
record/records are not added to Target.

## Host regression

Four new tests cover pack/open/facade with synthetic ELF, unavailable configuration
sources, immutability/delegation; stale profile hash rejection before preflight;
refusal to package after preflight ERROR; capsule/profile mismatch even after
updating the package file hash. Mock preflight PASS is not ELF validation evidence.
All previous 64 M2–M4/E1–E4 tests remain.

Actual ELF SHA256:
`d6bfed5a23f6d25935df02e4b5b0b4049c950c61313132cc99e1106c400f4206`.
Environment: Windows, xPack GDB 14.2.90.20240526-git, embedded Python; no backend
started. Raw package/ELF/logs remain gitignored; [result](../results/config-pipeline.json)
has no personal paths. Negative host outcomes are expected and asserted.

## Boundaries and next step

The main research end-to-end M4 path is verified, not production migration.
--package does not install config_props by itself; production agent/CTest do not
use the facade; SESSION_CONFIG exists only in the research wrapper. No Orange Pi/
SSH run. Previous core compatibility results remain historical, not new runs.

Before M5 agree on raw TOML base64 transport, defaults/version mismatch behavior,
legacy config_props and future API/user-name collisions. Q6/Q19 upper resource
bounds remain open. Next: consolidate accepted decisions and unresolved questions
before the normative specification revision. Core integration still requires
owner authorization.

Host validation: Linux CI 68/68 PASS; Windows 67 PASS/1 skip (no compiler on
PATH for CMake). Actual prepare and GDB smoke above ran on Windows.
