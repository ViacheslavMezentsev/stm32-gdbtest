# Candidate v0.2.0-rc.1: scope and acceptance

[Documentation](index.md) · [Русский](../ru/RC020_READINESS.md)

Agreed on 2026-10-03. Python `0.2.0rc1`, API specification **0.2.3**, API_VERSION=1,
api.toml schema=1, main specification **0.65**. Prepared locally; no tag or publication yet.

## Scope

- record/records, public RecordError and immutable config/config_props.
- Explicit SESSION_CONFIG, session.toml and captured TOML configuration in GDB/packages.
- Compatibility with legacy session.json, PROFILE_DIR and packages.
- Five CMSIS profiles, HAL F030, table checks and measurement statistics techniques.
- Frames/context, experimental read/finish, RTOS and adaptive scheduling are excluded from the API.

## Migration from v0.1.0-rc.2

1. Update the pinned module gitlink to the verified candidate SHA and rerun CMake configure.
   There is no pip distribution.
2. Existing PROFILE_DIR, target.toml, session.json and scenarios continue to work.
   Select SESSION_CONFIG explicitly to expose new TOML configuration.
3. Create session.toml with `[config]`, `target = "target.toml"`, `api = "api.toml"`;
   add `image = "full-image.toml"` for full-image. Paths are relative to session.toml.
4. Set `schema = 1`, `[records]` and optional user sections in api.toml.
   Unknown fields remain accessible; known limits are validated.
5. Do not combine SESSION_CONFIG with the legacy PROFILE selection or image overrides.
   session.json remains the generated execution descriptor; do not replace it manually with TOML.
6. record/records belong to one scenario invocation and do not export automatically.
   Run new configuration-capsule packages with the new module version.

Examples and limits: [API](API.md), [techniques](TESTING_TECHNIQUES.md),
[accepted results](API_ACCEPTANCE.md).

## Candidate verification

Candidate code: **972af7c**. Executable code has not changed since this SHA;
final preparation only corrected the obsolete version expectation in a host test.
[Machine-readable results](../releases/v0.2.0-rc.1-results.json) include runtime,
ELF, package and raw-report hashes, with individual stage statuses.

| Check | Result |
| --- | --- |
| Windows host | 164: 153 PASS, 11 platform skips |
| Linux Docker host, repeated after updating version expectation | 164: 160 PASS, 4 skips |
| Docker docs/format | PASS |
| GCC13/14/15 × five CMSIS profiles, HAL GCC13 | 15/15 CMSIS + HAL PASS |
| F030/ST-Link/OpenOCD lifecycle | 10/10 |
| F103/J-Link lifecycle | 10/10 |
| F411/ST-Link/OpenOCD lifecycle | 10/10 |
| F411/ST-LINK GDB Server 7.14 lifecycle | 10/10 |
| F030/OpenOCD lifecycle from a new package | 10/10 |
| Restoration BOOT/GPIO after five lifecycle runs | 10/10 |
| Consumer: legacy offline / SESSION_CONFIG offline | 3/3 + 3/3 |
| Consumer package / F411 HAL restoration | 1/1 + 2/2 |

Lifecycle covers build/prepare, boot/GPIO/strict, full-image A5, expected verify-only
ERROR with different fill, full-image FF, timeout/host recovery and subsequent GPIO.
10/10 counts stages, not ten unique hardware scenarios. Expected ERRORs remain in
reports. F030/F103 CMSIS and F411 HAL firmware were restored.

The isolated consumer is a real Git repository `c8dc670` with a mode-160000 gitlink
to `972af7c`, created from tracked minimal-consumer files; the owner's existing project
was not modified. The legacy → SESSION_CONFIG transition passed configure, build and
CTest. Original session.toml and api.toml were unavailable during the package hardware
run; the scenario verified config and record/records. Both files were then restored.

The initial Linux host run found the old `0.2.0.dev0` expectation in test_public_api.
After changing it to `0.2.0rc1`, all host checks passed. The initial failure remains
in the evidence. No runtime fix or additional programming was needed for that change.

Previous complete campaign: [accepted results](API_ACCEPTANCE.md).
The F103 Flash warning remains. Orange Pi/SSH is not rechecked in this stage.
Merge, signed tag and publication are separate owner actions after acceptance.

## Publication boundary and levels

Local research and prototypes are excluded from the candidate; `docs.public` is
mandatory. Accepted conclusions and reproducible checks are in
[API_ACCEPTANCE](API_ACCEPTANCE.md). API specification 0.2.3 clarifies public sources
and the candidate version without method changes. Main revision 0.65 defines L0–L6.
The matrix above covers L1–L6. L0 verification in the pinned image passed:
verify.py confirmed tool versions and GDB-Python for GCC 13/14/15.
The image was not rebuilt and original archive checksums were not rechecked.
After isolating the experimental host test and adding publication checks, the final
public suite was checked separately; the preceding 164 count refers to the initial candidate.

Final clean public snapshot: docs/spec/API-spec/links/pairs/public, format,
host and HAL — **8/8 PASS**. Host: Windows 144 PASS/11 skips,
Linux 151 PASS/4 skips (155 tests). From 164, 14 local simulation tests were removed
and five publication checks added. Public core benchmark: 13 shapes and five boundaries PASS.
Runtime matches hardware-tested 972af7c; changes affect CI/docs/publication scope.
All 278 excluded files remain byte-for-byte intact locally; Git history was not rewritten.
