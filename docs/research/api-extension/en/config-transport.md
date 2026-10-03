# M4: snapshot transport and CMake wrapper

[Study](index.md) · [Русский](../ru/config-transport.md)

2026-10-03. Continues [M2/M3](config-loader.md), baseline 5a4a774. Research sources:
[transport](../../../../tests/api-extension/config_transport.py),
[bridge](../../../../tests/api-extension/session_bridge.py),
[CMake](../../../../tests/api-extension/cmake/research.cmake).
Production CLI/CMake/runner/Target/package and firmware are unchanged.

## Transport

The JSON envelope contains original session/target/api/image bytes as base64 plus
SHA256, not a JSON conversion of parsed TOML. The receiver validates envelope,
hashes and file set, reparses captured bytes with TOML, validates, applies defaults
and creates immutable config/config_props. Original paths are never opened.
A defaults fingerprint rejects mismatching defaults rather than silently changing
behavior on the receiver. Experimental research-config/1 is not a production
package or API version change.

Verified date, local/offset datetime, microsecond time, integer, bool, Unicode,
nested arrays/tables, ±Inf, NaN and negative zero. Unknown fields/source hashes
survive; props.data has no defaults. Special floats in unknown TOML data do not
expand record() types. Corrupted base64/hash/schema/defaults/file sets and duplicate
JSON keys are rejected. Updating a hash does not bypass known-field validation.

The experimental ZIP contains only config.json. It reopens after the temporary
source directory is removed, modelling unavailable original paths, not an actual
Orange Pi/SSH run. Neither archive nor envelope is integrated into ddtt-package.

## CMake and compatibility

research_attach calls unchanged stm32_gdbtest_attach. Legacy mode produces the
ordinary eight-field JSON. New mode selects target through the shared Python loader
and generates separate research-session.json with session_config/profile; PROFILE
conflicts are rejected. Actual CMake configure/generate uses Ninja/ARM GCC in Docker.
Registered production CTest commands still use old JSON; bridge separately checks
the new descriptor. This is not finished CTest/config integration.

Bridge checks descriptor target-path agreement, captures API changes without a build
and retains previous snapshots. Stale-path detection does not replace ELF/manifest
validation for changed target contents at the same path; core checks remain necessary.

Actual legacy F030 HW_CI_ADC_UNITS prepare-only: PASS, contracts PASS,
connection_attempted=false; ELF SHA256 starts d6bfed5a. No hardware connection.
Linux core host regression: 114 tests, 4 platform skips, PASS.

## Results and retained failures

- Windows: 64 tests, 63 PASS and one CMake skip (no cc/ARM GCC on PATH).
- Linux CI: 64/64 PASS including CMake old/new/conflict.
- Initial Linux run also skipped CMake because the fixture searched only cc.
  Enabling installed ARM GCC exposed FAIL "No hardware cases found": production
  collect correctly rejected the empty test directory. Added a collectible dummy
  case never executed on MCU; corrected run 64/64 PASS.
- Initial skip/FAIL are retained; they are not successful CMake evidence.

## Next

M4 is partial. Next substage: research end-to-end descriptor → prepare → package →
restored snapshot → scenario facade, stale manifest, legacy packages and changed cwd;
legacy source/props needs an exact contract. Actual GDB-agent transfer, new production
prepare/package and remote execution remain unverified. Final transport and defaults
compatibility policy need decisions; fingerprint is a tested candidate, not approved.
M5/core integration not started; Q20 remains open.
