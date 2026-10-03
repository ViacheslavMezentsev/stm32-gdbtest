# Q20: migration to session.toml

[Study](index.md) · [Русский](../ru/session-migration.md)

2026-10-03. Integration proposal based on 74cc842. File composition and
config/config_props are approved; M1 is approved: explicit SESSION_CONFIG, retained JSON/legacy mode and conflict
refusal. Remaining implementation details are a proposal. No core changes or new hardware runs.

## Current behavior

STM32GDBTest.cmake selects PROFILE or PROFILE_DIR/target.toml, generates eight-field
session.json and registers CTest with --session <JSON>. CLI reads JSON directly;
runner independently selects image policy from --image-policy/environment. Simply
giving scripts a TOML reference is insufficient: image verification and scenarios
must use the same settings. package.py explicitly includes ELF, target, scenarios
and manifest; new configuration files are not included automatically.

## 1. User configuration and build description

Retain internal session.json, with session.toml owning api/target/image selection
in the new mode:

```toml
# profile/session.toml
[config]
api = "api.toml"
target = "target.toml"
image = "full_image.toml"
```

Propose explicit CMake SESSION_CONFIG:

```cmake
# Proposed syntax, not implemented
stm32_gdbtest_attach(firmware
    PROFILE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/profile"
    SESSION_CONFIG "${CMAKE_CURRENT_SOURCE_DIR}/profile/session.toml")
```

PROFILE_DIR retains scenarios/requirements/contracts responsibility, not an
additional target source. Reject simultaneous SESSION_CONFIG and PROFILE: the new
mode selects config.target. Without SESSION_CONFIG preserve legacy behavior,
including PROFILE and existing precedence. No automatic session.toml discovery.

Add session_config to generated JSON; ELF/GDB/tests/root/out/stand and manifest
remain build-integration data. Retain profile if internal consumers require it,
but derive it from config.target and check agreement rather than having two sources.
Users need not edit the eight old fields. run --session <generated JSON> is unchanged.
Direct --session session.toml is not proposed yet: TOML has no ELF/GDB/tests/out.

## 2. Shared loading mechanism

1. One host loader reads TOML and referenced files, resolves paths relative to TOML,
   validates known settings and retains unknown api.toml fields. CMake uses this
   Python mechanism for target selection, not an independent TOML parser.
2. During run preparation, runner captures bytes, parsed data and defaults once.
   Image checks and GDB config/config_props use the same image/target snapshot.
   No source rereads inside GDB; ELF/manifest consistency checks remain mandatory.
3. Configure and run preparation are different phases, not permanent caching.
   Within a run, hashes/data share one read per file. Later edits do not affect it.
4. CMake tracks session.toml and selected target. Changed target selection requires
   regeneration/manifest refresh; stale selection is rejected before connection.
   api/image are separate run inputs; changing journal limits alone should not
   require firmware recompilation.

## 3. Conflicts and absence

Propose preventing CLI/environment overrides of config.api/target/image in new
mode. --image-policy or STM32_GDBTEST_IMAGE_POLICY produces preconnection ERROR
identifying the conflict. Select another session.toml for another image policy;
even identical duplicate references are not permitted as a second source.
Without config.image retain the approved ELF-section behavior; environment cannot
silently select another policy.

--stand, --timeout and --identity-policy retain current roles: no corresponding
new TOML keys exist. config covers api/target/image and does not promise every
process parameter. Stand/timeout access would be a separate schema extension.
Legacy mode retains existing CLI/environment precedence. Errors in explicitly
selected TOML/files never fall back to legacy mode.

## 4. Stand transfer and compatibility

pack/--package and remote runs must transfer content snapshots, not depend on
original absolute paths. reference retains the original diagnostic link; extraction
paths do not replace its meaning. Verify raw-byte integrity and parsed-data agreement.
TOML types such as dates/times need explicit portable representation; do not silently
stringify them or discard unknown keys for JSON convenience.

Evaluate package manifest/report schema impacts separately, without automatically
assigning versions. Old packages/JSON launches belong in regression. Legacy-mode
config/config_props requires an explicit contract: target from profile, API defaults,
image from the actual selected policy. Metadata must not invent session.toml;
its precise legacy form remains an unresolved Q20 detail.

## 5. Work sequence and criteria

| Step | Result |
| --- | --- |
| M1 | Approve explicit SESSION_CONFIG, retained JSON and conflict rules |
| M2 | Research-only host loader prototype and independent TOML fixtures; no MCU required |
| M3 | Test required/optional inputs, types/ranges, defaults, unknown keys, nested immutability, hashes, paths and provenance |
| M4 | Test legacy/new modes, CMake configure/prepare, target/API changes, packing and all TOML types in transport |
| M5 | After contract approval, add API spec requirements and overall spec system requirements/references |
| M6 | After integration authorization, integrate, regress and run agreed first-package hardware acceptance |

M3/M4 negatives: missing target; absent api versus selected nonexistent api;
invalid known field alongside valid unknown data; source edits after capture;
CLI/env conflict; stale manifest; changed cwd; remote host without source tree.
These are planned checks, not obtained results. Q20 remains open.

[M2/M3: host configuration prototype](config-loader.md) — 12 new tests, Windows 56/56 including E1–E4, initial CRLF test-expectation FAIL retained. Next M4; core unchanged.

[M4: transport and CMake](config-transport.md) — Linux 64/64, Windows 63 PASS/1 skip; JSON/config-ZIP, actual old/new/conflict configure, legacy prepare PASS. M4 partial: production package/agent not integrated.

[M4: end-to-end pipeline](config-pipeline.md) — real F030 ELF prepare PASS, production package, GDB-Python 6/6 without MCU; Linux 68/68, Windows 67 PASS/1 skip. Next: remaining contract decisions before M5.

### Approved: TOML transport and defaults compatibility — 2026-10-03

Owner decision: transfer original selected TOML bytes as base64 in internal JSON
with SHA256. The receiver verifies hashes and parses transferred bytes without
opening original paths. TOML types and unknown fields survive; scenarios see
ordinary immutable config/config_props, not base64 API values.

Preparation and execution defaults must match. Mismatch produces ERROR before
connection, with no automatic receiver-default substitution. Use a compatible
tool version or prepare the package again. M4 tested a defaults fingerprint;
the envelope algorithm/version will be fixed during integration. Matching defaults
alone does not prove compatibility of all other versioned contracts.

This part of Q20 is approved; legacy config_props, bounds/name collisions and
integration details remain. Normative API 0.1.0 and core are unchanged.

### Approved: legacy-mode config/config_props — 2026-10-03

Owner decision: launches without session.toml retain existing selection rules,
while the new read interface uses the same shape:

| Section | config | config_props |
| --- | --- | --- |
| target | Actual profile loaded via session.json | data/sha256/reference of the selected file |
| api | Default API settings | None: no API file selected |
| image | Actual CLI/environment-selected policy or None | data/sha256/reference of the selected file or None |

Legacy-package properties describe the packaged file, not an invented original-host
path. No session.toml is fabricated. Immutability, byte/hash consistency and the
source/defaults distinction remain identical. Old scenarios need not use new properties.

This is an accepted requirement, not completed integration. Prior legacy regressions
do not prove these properties exist in production Target. Test the adapter separately
before new-core acceptance. Q20 remains open for integration details and future name
collisions; numeric bounds belong to Q6/Q19.
