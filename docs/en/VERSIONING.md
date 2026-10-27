# Versions and releases

[Documentation](index.md) · [Русский](../ru/VERSIONING.md)

Current line: **0.5.x / API_VERSION=3**. [Release transitions](RELEASE_CHANGES.md).
Use SemVer MAJOR.MINOR.PATCH with a v-prefixed tag. Before 1.0, compatible fixes and docs
change PATCH; new features or incompatible APIs change MINOR with migration. Published tags
are never moved. Package version comes from `__version__`; API and configuration schemas
are independent. Python/GDB versions and specification revisions are separate quantities.

Commands below are templates for a future accepted release, not authorization to publish a tag.

## Before a release

1. Host and offline checks: CI is green on the final commit ([checks and CI](testing.md)).
2. Hardware acceptance on the final SHA: F030R8, F103, F401CC, F411CE and
   F429ZI with ST-Link/OpenOCD, plus AT32F403A with OpenOCD/J-Link WinUSB.
   A second F411 backend does not replace F103. Scope, authorization and restoration
   are defined in the [P5 matrix](../development/release-050-acceptance.md) (Russian).
   Other backends and SSH need separate checks; a local PASS does not cover them.
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
git tag -s v0.5.1 -F docs/releases/v0.5.1.md --cleanup=verbatim
git push origin v0.5.1
```

`--cleanup=verbatim` keeps the text as is: without it git drops lines starting with
`#`. The same file is the GitHub release text (Releases → Draft a new release; for
`-rc` tick "Set as a pre-release") or `gh release create v0.5.1 -F
docs/releases/v0.5.1.md` (`--prerelease` for candidates).

The notes have no Markdown headings (lines starting with `#` vanish from the tag message under normal
cleanup and render large on GitHub). Russian text first; English is the same text in a collapsed
`<details><summary>English</summary>` … `</details>` block with a blank line after `<summary>` and before
`</details>`, otherwise GitHub does not render its Markdown. The final check matrix may be a Markdown table
(stand × GDB version). Contents: the first line `stm32-gdbtest <version> — <gist>`; the purpose
in one or two sentences; package version, `API_VERSION`, specification revision;
"Highlights" — 5–8 user-relevant items from the CHANGELOG; "Final check" — the commit
and the result matrix; "Limits"; links to CHANGELOG and STATUS.
GitHub turns `@name` into a user mention (the user appears among the release
contributors) and `#number` into an issue link, so write such fragments only in
backticks: `` `@case` ``.

Branch and commit rules — [maintenance](maintenance.md).

## Moving to 0.5.0: emulators

The general consumer migration is described in [MIGRATION_050](MIGRATION_050.md).
Existing hardware target schemas 1/2 and stands need no migration. For a new local
emulator route, create a separate schema 3 target with environment=emulator and
a stand with [emulator] and [qemu] or [renode]. Do not carry over hardware identity
or full Flash programming policy. reset currently refuses before a command.
Configuration and limits: [QEMU](QEMU.md), [Renode](RENODE.md).
