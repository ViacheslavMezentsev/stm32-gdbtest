# DDTT colouring in VS Code

[Documentation](index.md) · [Русский](../ru/DDTT_COVERAGE.md)

The external `tools/ddtt_coverage.py` tool projects saved check results into LCOV.
This example package targets candidate 0.4.2; the core, Target API and result.json format are unchanged.
The developer supplies each association: **scenario → check name → source line**.

## Colour semantics

| Mark | DDTT meaning |
| :--- | :--- |
| Green, DA=1 | The named check ran and confirmed its expectation |
| Red, DA=0 | The named check ran and failed its expectation |
| No mark | No association or usable evidence; see the JSON reason |

DA is a Boolean check verdict, not an instruction execution count. Reader percentages cover only
exported lines; inspect UNKNOWN in `ddtt-evidence.json` for completeness. One check does not colour
an entire function automatically. Any FAILED check makes a shared line red; UNKNOWN remains in the
sidecar even when another check makes that line green. A scenario FAIL does not erase a completed
successful check; ERROR/SKIP scenarios produce no marks.

## Why fewer lines than tests?

The initial hardware example mapped seven points from five scenarios. Files such as `test_app.py`,
`test_board.py`, `test_boot.py`, `test_ddtt_feedback.py` and `test_injection.py` do not identify C++ lines.
Stand configuration, MCU identity and scenario checks may have no appropriate firmware source line.

The [BluePill template](../../examples/ddtt-coverage/bluepill.template.json) now also maps setup
completion and timestamp writers. [BlackPill](../../examples/ddtt-coverage/blackpill.template.json)
illustrates GPIO, ADC failure and IRQ publication. Additional associations only become coloured after
running their scenarios. Expand the map by specific checks, not by test file count.

## Repeatable workflow

Requires Python 3.11+, a built ELF, its sources and a dedicated campaign results directory.
Run from the stm32-gdbtest checkout; replace sample paths. PowerShell:

```powershell
$project = 'D:/work/stm32-hwtest-bluepill'
$elf = "$project/build/debug/firmware.elf"
$campaign = "$project/build/ddtt-campaign"
python examples/ddtt-coverage/bind_map.py --project $project --elf $elf --template examples/ddtt-coverage/bluepill.template.json --out "$campaign/map.json"
# Run selected scenarios with the regular runner/CTest into $campaign/runs.
# Clear previous colouring in the dedicated view directory before starting:
New-Item -ItemType Directory -Force "$campaign/view" | Out-Null
Set-Content -LiteralPath "$campaign/view/lcov.info" -Value ''
# Export after the runner finishes, including FAIL/ERROR:
python tools/ddtt_coverage.py --project $project --map "$campaign/map.json" --runs "$campaign/runs" --out "$campaign/view"
```

`--runs` reads only immediate `*/result.json` children. Do not select an entire historical archive.
`--out` must be a separate presentation-only directory; keep input maps and sources elsewhere.
Do not regenerate a map to bypass a hash mismatch: rebuild and rerun the scenarios first.
The existing runner builds, executes and cleans up hardware; the exporter never connects to a board.
The same Python commands work on Linux with shell-appropriate paths.

The example `bind_map.py` validates unique anchors and records ELF/source SHA-256 hashes.
It does not prove the sources were compiled into the ELF: the result's build_manifest supplies that check.
`anchor` matches a complete line with outer whitespace stripped; inner whitespace matters.
`check` is the exact name in result.json, including interpolated values. Repeated names are confirmed
only if all executed checks with that name passed. `source` is project-relative, using `/`.

## VS Code

Install [Coverage Gutters](https://github.com/ryanluker/vscode-coverage-gutters).
Set an **absolute path** in workspace settings:

```json
{
  "coverage-gutters.manualCoverageFilePaths": ["D:/work/stm32-hwtest-bluepill/build/ddtt-campaign/view/lcov.info"],
  "coverage-gutters.showLineCoverage": true,
  "coverage-gutters.watchOnActivate": true
}
```

Open a project C++ file and run `Coverage Gutters: Display Coverage` or `Watch` from the command palette.
The extension rereads LCOV after export. SF uses absolute paths on this machine; re-export with the new
host's `--project` after moving artifacts. Other readers can consume LCOV, but automatic GitHub/GitLab
integration and their percentage interpretation have not been verified here.

## Avoiding stale green marks

The latest selected hardware attempt per scenario wins, ordered by timezone-aware `started_utc`.
Equal latest timestamps are UNKNOWN. A newer ERROR or incompatible ELF never falls back to an old PASS.
Prepare is excluded. ELF, source and build_manifest evidence must match. Missing checks, unsuitable
status or manifest produce UNKNOWN with a reason, without DA=0.
Invalid maps, changed sources, ambiguous anchors or malformed JSON return command code 2, empty LCOV
and an ERROR sidecar, invalidating previous colouring. Successful export returns 0 even with
FAILED/UNKNOWN points: processing success is separate from scenario acceptance.

Outputs: `lcov.info` and `ddtt-evidence.json` (schema 1). JSON retains every point, UNKNOWN reasons,
result.json path and SHA-256, run_id, scenario status, check verdicts and state counts.
Hashes associate artifacts but are not cryptographic signatures of results.

## Verified foundation and limits

On 2026-10-15 the original workflow passed five selected scenarios in two fresh campaigns on
BluePill/F103CB and BlackPill/F411 with OpenOCD, yielding seven confirmed lines. The owner confirmed
VS Code display. The public exporter adds host regressions for stale evidence, errors and conflicts.
Accepting additional template associations does not constitute hardware verification of those points.
This is a DDTT evidence view; FPB observers, function tracing and manual debugpy debugging are outside
this tool's scope.

## Tool compatibility

Maps without `environment` retain hardware semantics. Use `environment: "emulator"` for a separate emulator map. Missing `purpose` means automated; manual is excluded. A line with CONFIRMED and UNKNOWN is now omitted from LCOV unless FAILED is also present. Rebind maps anchored to comments. See [portable reports](PORTABLE_DDTT.md).
