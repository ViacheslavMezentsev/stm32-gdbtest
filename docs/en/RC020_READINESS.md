# Candidate v0.2.0-rc.1: scope and acceptance

[Documentation](index.md) · [Русский](../ru/RC020_READINESS.md)

Agreed on 2026-10-03. Python `0.2.0rc1`, API specification **0.2.2**, API_VERSION=1,
api.toml schema=1, main specification **0.64**. Prepared locally; no tag or publication yet.

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
[integration](../research/api-extension/en/core-integration.md).

## Candidate verification

In progress. Previous hardware results do not verify the current SHA.
Plan: full Docker docs/format/host, GCC13/14/15 × five CMSIS profiles;
HAL GCC13; a real consumer Git submodule; Windows lifecycle F030/OpenOCD,
F103/J-Link, F411/OpenOCD and F411/ST server, with restoration.

Previous complete campaign: [103 CMSIS + 22 HAL + one example](../research/api-extension/en/scenario-migration.md).
The F103 Flash warning remains. Orange Pi/SSH is not rechecked in this stage.
Merge, signed tag and publication are separate owner actions after acceptance.
