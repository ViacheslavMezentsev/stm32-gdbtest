# Legacy: config/config_props without session.toml

[Research](index.md) · [Русский](../ru/legacy-config.md)

2026-10-03. Isolated [legacy_config.py](../../../../tests/api-extension/legacy_config.py)
captures views for an already selected JSON descriptor or extracted old package.
This studies system spec 5.20.10–5.20.11; core, CLI and agent remain unchanged.
The loader is invoked explicitly; production Target does not expose these properties yet.

## Verified behavior

| Case | Result |
| --- | --- |
| Legacy profile without optional files | Actual target file; api defaults with props.api=None; image=None in both views |
| Neighboring session.toml/api.toml | No automatic discovery, even for invalid session.toml |
| Image selection | Explicit argument precedes STM32_GDBTEST_IMAGE_POLICY; invalid selected files do not fall back |
| Internal image_policy_path | No additional authority: runner derives it from argument/environment |
| Capture and source changes | One read per file; data and SHA256 describe captured bytes; snapshot survives removed paths |
| Immutability | Nested tables/lists and facade properties reject mutation |
| Old package | Production pack/open_package; after moving original sources, references identify actual extracted files |
| Image policy included in ZIP | Inclusion does not activate it; explicitly select its extracted path |
| Invalid TOML/range/unknown target and image fields | Validation rejects them, preserving strict schemas |

As in the current runner, relative paths resolve from process cwd, not the session.json
location. session.toml path semantics are not imposed on legacy mode.
session_sha256=None: no fictional session.toml or API-default source is fabricated.

## Evidence

[Six tests](../../../../tests/api-extension/test_legacy_config.py) use real validators
and production packaging. ELF is synthetic, never executed and not firmware PASS.
Package GDB lookup is mocked in the test; the entire suite also runs inside real GDB Python.

- Windows: 79 tests, 78 PASS / 1 CMake skip (no compiler in PATH).
- Linux Docker: 79/79 PASS; CI documentation: 4/4 PASS.
- GDB14/Python3.11.4 and GDB16/Python3.13.12: 6/6 PASS each.
- [GDB14](../results/legacy-config-gdb14.json), [GDB16](../results/legacy-config-gdb16.json).
- [Initial FAIL](../results/legacy-config-initial-failure.json): expected value compared a frozen snapshot with ordinary load_profile lists. Corrected expectation; loader unchanged.

Host: `python -B -m unittest discover -s tests/api-extension -q`.
GDB: import run_legacy_config from tests/api-extension and call
`run_legacy_config.run('<result.json>')`; include repository root in sys.path too.
Use `-nx -batch -q -iex "set auto-load off"`, without ELF or target remote.

## Boundaries and next step

Selected-file properties and isolated snapshots are verified. Production runner still
reads its own files; binding snapshots to prepare/agent and verifying a single source
in real execution remains integration work. New-mode transport is unchanged: legacy
snapshots are not passed to dumps, which expects session.toml. Old packages acquire
neither a new format nor implicit image selection.

Next: consolidate first-package readiness into verified behavior, prototype work and
integration requirements. Numeric bounds Q6/Q19, RecordError import/base class and
separate owner approval remain prerequisites for core integration. Earlier M5 notes
about unverified legacy views describe that earlier stage; production integration
is still pending.
