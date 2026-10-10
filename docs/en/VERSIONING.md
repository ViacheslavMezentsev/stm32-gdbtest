# Versions and releases

[Documentation](index.md) → Versions · [Русский](../ru/VERSIONING.md)

[Release v0.3.0](../releases/v0.3.0.md): Python version 0.3.0; the extended API is accepted on five boards in six run layouts; the owner publishes the tag.

[rc.2 plan](RC2_READINESS.md): tag `v0.1.0-rc.2`, Python `0.1.0rc2`; published at a0d6547.

The format is MAJOR.MINOR.PATCH per [SemVer 2.0.0](https://semver.org/spec/v2.0.0.html);
Git tags have the `v` prefix. The current release is **v0.3.0**, Python **0.3.0**; the owner sets its tag.
The release branch prepares **v0.4.0** (Python 0.4.0, API_VERSION=2); it is not yet a published tag.
Candidates v0.2.0-rc.1 and v0.3.0-rc.1 were never published. The previous published candidate is `v0.1.0-rc.2`.
The initial export from the stand project is not a release.

Before 1.0: compatible fixes → 0.1.1; new features or API changes → 0.2.0 with an
explicit migration. PATCH never breaks the API. After 1.0: incompatible API → MAJOR,
compatible features → MINOR, fixes → PATCH. 0.x versions do not promise 1.0
stability. A published tag is never moved: a fix gets a new version. The consumer's
gitlink pins the SHA; a tag makes selecting that SHA easier.

The version source is `__version__` in `stm32_gdbtest/__init__.py`. For future Python
packaging the tag `v0.1.0-rc.1` maps to Python version `0.1.0rc1` and `v0.1.0` to
`0.1.0`. `API_VERSION` and the JSON/TOML schema numbers are independent of the release
version and change only when the corresponding contract changes.

The API 0.3.0 design is the [API audit and redesign](API030_PLAN.md). The 0.4.0
scope and migration are in the [release map](RELEASE040_SCOPE.md); final acceptance
and publication are tracked in [TODO](../../TODO.md).

## Before a release

1. Host and offline checks: CI is green on the final commit ([checks and CI](testing.md)).
2. Hardware check of the CI firmware with `run_hw.py` on the final commit on six stands:
   F030R8/OpenOCD, F401CC/OpenOCD, F411CE/OpenOCD, F411CE/ST-LINK GDB Server,
   F429ZI/OpenOCD and AT32F403A/J-Link. The set is agreed with the owner: the bench has
   one J-Link, so the AT32 board replaces F103C8.
3. Consumer integration through a real Git submodule; if needed, agreed hardware and
   recovery checks of the consumer.
4. Documentation and migration match the code; LICENSE is present; no local artifacts
   in the commit. The actual check matrix and known limits are stated.
5. `__version__` is updated, a dated CHANGELOG section is opened (RU and EN),
   `[Unreleased]` is kept for future changes; a "release" specification revision is issued.
6. The release branch contains the release notes `docs/releases/<tag>.md` (section below).
7. Merge into main, then tag the merge commit. The owner publishes; the name is
   checked before a package is published.

## Tag and release notes

The tag is annotated and signed; its message is the release notes file:

```powershell
git tag -s v0.1.0 -F docs/releases/v0.1.0.md --cleanup=verbatim
git push origin v0.1.0
```

`--cleanup=verbatim` keeps the text as is: without it git drops lines starting with
`#`. The same file is the GitHub release text (Releases → Draft a new release; for
`-rc` tick "Set as a pre-release") or `gh release create v0.1.0 -F
docs/releases/v0.1.0.md` (`--prerelease` for candidates).

The notes have no Markdown headings (lines starting with `#` vanish from the tag message under normal
cleanup and render large on GitHub). Russian text first; English is the same text in a collapsed
`<details><summary>English</summary>` … `</details>` block with a blank line after `<summary>` and before
`</details>`, otherwise GitHub does not render its Markdown. The final check matrix may be a Markdown table
(stand × GDB version). Contents: the first line `stm32-gdbtest <version> — <gist>`; the purpose
in one or two sentences; Python version, `API_VERSION`, specification revision;
"Highlights" — 5–8 user-relevant items from the CHANGELOG; "Final check" — the commit
and the result matrix; "Limits"; links to CHANGELOG and STATUS.
GitHub turns `@name` into a user mention (the user appears among the release
contributors) and `#number` into an issue link, so write such fragments only in
backticks: `` `@case` ``.
Example — [v0.3.0](../releases/v0.3.0.md); the former `---` format — [v0.1.0-rc.1](../releases/v0.1.0-rc.1.md).

Branch and commit rules — [maintenance](maintenance.md).
