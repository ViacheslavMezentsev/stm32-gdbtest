# M2/M3: host session configuration prototype

[Study](index.md) · [Русский](../ru/config-loader.md)

2026-10-03. Following owner approval of [M1](session-migration.md), implemented
isolated [session_config.py](../../../../tests/api-extension/session_config.py).
Core, CLI/CMake and normative API spec 0.1.0 are unchanged; no MCU connections.

## Verified scope

- session.toml selects target/api/image, with paths relative to its directory.
- target required; absent api gives defaults, absent image gives None. Explicit
  missing/invalid files fail without fallback.
- Known records fields require positive integers excluding bool; schema=1 is
  required for an existing api.toml. E1 defaults remain experimental; upper bounds
  are neither approved nor verified resource guarantees.
- Unknown fields/sections, nested arrays and TOML dates/times survive locally.
  This does not prove JSON transport.
- config contains defaults; config_props.data does not. SHA256 hashes original
  bytes; reference is the original link. Views are immutable: MappingProxyType
  dictionaries and tuple arrays.
- Each selected source is read once per load. Edits after capture do not affect
  the snapshot; a new invocation sees new data. This does not promise an atomic
  multi-file filesystem snapshot.
- PROFILE/image-policy arguments and image-policy environment conflict before
  configuration reads in new mode. Legacy mode is not implemented by this prototype.

Prototype session schema is narrow: only [config] and target/api/image. Unknown
field acceptance applies to api.toml, not the system file selector. ConfigError
codes are research diagnostics, not approval of RecordError under Q18.

## Existing validation

Image uses existing validate_policy; target uses load_profile. To avoid rereading
the source target or changing core, captured bytes are written to a temporary file
for the existing validator. This adapter is experiment-only; integration should
extract pure dictionary validation and remove temporary I/O. No duplicate target
schema implementation was introduced.

## Tests and boundaries

[12 new tests](../../../../tests/api-extension/test_session_config.py) use independent
text fixtures, temporary files and negatives. Combined with E1–E4: 56 tests.
Initial Windows run: 55 PASS, 1 FAIL because a hash expectation used LF while the
file was written with CRLF. The test now hashes actual original bytes; corrected
run: 56/56 PASS. Hash implementation unchanged. This was a test-expectation defect,
not hardware ERROR; history is retained in the registry.

Final validation: Windows 56/56 PASS, Docker CI Linux 56/56 PASS; docs 4/4 PASS.

M2 complete; M3 covers the local host scope above. M4 remains: CMake/prepare,
stale manifest, packaging, remote transport and legacy mode. MappingProxyType and
date/time cannot simply use current JSON; a transport experiment must verify
type and unknown-field retention. Actual Target attributes and integrated core
acceptance are not implemented. Q6/Q19 resources, numeric bounds and future API-name
collisions remain unresolved. Core integration is not authorized.
