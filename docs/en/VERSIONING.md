# Versions and releases

[Documentation](index.md) → Versions · [Русский](../ru/VERSIONING.md)

The format is MAJOR.MINOR.PATCH per [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html);
Git tags have the `v` prefix. The first candidate is **v0.1.0-rc.1**, the first release
**v0.1.0**. The current version is the candidate `0.1.0rc1` (tag `v0.1.0-rc.1`); the
initial export from the stand project is not a release.

Before 1.0: compatible fixes → 0.1.1; new features or API changes → 0.2.0 with an
explicit migration. PATCH never breaks the API. After 1.0: incompatible API → MAJOR,
compatible features → MINOR, fixes → PATCH. 0.x versions do not promise 1.0
stability. A published tag is never moved: a fix gets a new version. The consumer's
gitlink pins the SHA; a tag makes selecting that SHA easier.

The version source is `__version__` in `stm32_gdbtest/__init__.py`. For future Python
packaging the tag `v0.1.0-rc.1` maps to Python version `0.1.0rc1` and `v0.1.0` to
`0.1.0`. `API_VERSION` and the JSON/TOML schema numbers are independent of the release
version and change only when the corresponding contract changes.

## Before a release

1. Host and offline checks: CI is green on the final commit ([checks and CI](testing.md)).
2. Hardware check of the CI firmware with `run_hw.py` on the final commit on the
   F030R8/J-Link, F103C8/J-Link, F411CE/OpenOCD and F411CE/ST-LINK GDB Server stands.
3. Consumer integration through a real Git submodule; if needed, agreed hardware and
   recovery checks of the consumer.
4. Documentation and migration match the code; LICENSE is present; no local artifacts
   in the commit. The actual check matrix and known limits are stated.
5. `__version__` is updated, a dated CHANGELOG section is opened (RU and EN),
   `[Unreleased]` is kept for future changes; a "release" specification revision is issued.
6. Merge into main, then tag the merge commit. The owner publishes; the name is
   checked before a package is published.

Branch and commit rules — [maintenance](maintenance.md).
