# API 0.4.0 acceptance scenarios

[Documentation](index.md) · [Русский](../ru/API040_SCENARIOS.md)

Four additional scenarios labelled `api040`, shared by the five STM32 profiles. They use the existing
CMSIS firmware without new test hooks. This checks new package capabilities, not the entire API or
every GDB/backend combination.

| Scenario | Demonstrates | Expected outcome |
| --- | --- | --- |
| [HW_CI_040_RECORDS](../../tests/firmware/common/tests/board/test_release040_records.py) | MCU state, transition, measured counter increment and arbitrary diagnostics in one journal; independent copies | PASS, four records |
| [HW_CI_040_SKIP](../../tests/firmware/common/tests/board/test_release040_skip.py) | Configuration applicability, a decision via records, whole-scenario termination and finally execution | PASS with true; SKIP with false |
| [HW_CI_040_SKIP_VALIDATION](../../tests/firmware/common/tests/board/test_release040_skip_validation.py) | Refuses empty/non-string/invalid Unicode reasons and a limit overflow; subsequent navigation still works | PASS, six expected refusals |
| [HW_CI_040_STRING_VIEWS](../../tests/firmware/common/tests/board/test_release040_string_views.py) | One RAM buffer as char[3], char[] and char*: bounded reading without changing memory | PASS |

## Configuration and selection

Enable journal capture in `session.toml` (edit the section if already present):

```toml
[results]
capture = true
```

Control only example applicability in the selected `api.toml`:

```toml
[user.release040]
optional_loop = false
```

The default is true: the ordinary shared suite does not acquire a mandatory SKIP.
False models an explicitly disabled capability, not a broken board. An invalid type is FAIL.
Keep independent configurations and output directories for the two variants.
Do not change target.toml or the ELF to select scenarios: they must match the build manifest.

After the ordinary firmware build, select one ID; other scenarios do not run:

```text
python -m stm32_gdbtest run --session <session.json> --test HW_CI_040_RECORDS --stand <stand.toml> --prepare-only
python -m stm32_gdbtest run --session <session.json> --test HW_CI_040_RECORDS --stand <stand.toml>
```

Repeat for all four IDs; run SKIP with true and false (five hardware runs per board).
Use the normal CMake/session configuration so the descriptor references the selected session.toml.
The expected SKIP exit code is **77**, not 0. The general `run_suite.py` expects PASS: this campaign
uses explicit CLI selection instead of running the entire suite. [skip contract](api/skip.md).

## Artifact checks

- Every hardware run: verified image, normal reset/run teardown and confirmed server completion.
- PASS: `capture.status=saved`, `completion=normal`; SKIP: saved/interrupted, nonempty skip_reason, JUnit skipped.
- Disabled runs contain capability and optional.finally, but neither optional.executed nor optional.completed.
- Enabled runs contain all four records and do not increment the skip count.
- RECORDS retains distinct types: 0, false, null and the integer `2**60+1`. Sequence is order, not time.
- Generic export keeps **all** records. A measurement projection is explicit; record names do not define types.

Build selection.json from only the new hardware runs, then use
[results export, verify and report](RESULTS.md). Check file-processing outcomes separately from scenario verdicts:
successful HTML generation does not turn SKIP into PASS. Preserve original errors and subsequent attempts.

## Results

Verified on 2026-10-10: Windows, xPack 13.3.1-1.1 (GDB 14.2.90, Python 3.11.4),
SSH → OrangePi/Ubuntu 20.04, st-util 1.9.0 with libusb 1.0.27. Runtime base: `3613a00`;
the four new scenarios were tested in the working tree and preserved with source hashes.

| Board | Preparation | Hardware outcomes | Capture / JSON / JUnit |
| --- | --- | --- | --- |
| F030R8 | 5 PASS | 4 PASS + 1 expected SKIP | 5/5 |
| F103 / WeAct BluePill-Plus | 5 PASS | 4 PASS + 1 expected SKIP | 5/5 |
| F401CC | 5 PASS | 4 PASS + 1 expected SKIP | 5/5 |
| F411CE | 5 PASS | 4 PASS + 1 expected SKIP | 5/5 |
| F429ZI | 5 PASS | 4 PASS + 1 expected SKIP | 5/5 |

Total: 25 prepare PASS, 20 HW PASS and 5 expected SKIP (exit 77). All 25 hardware runs confirmed
image verification, teardown, idle and remote server exit 0. Capture retained 65 records;
generic export equals the original journals. A separate projection of five measurements yields
five values of 1 tick while retaining all 20 records of the selected runs. Export/verify/report
succeeded; HTML separates 20 PASS from 5 SKIP. Docker docs+host: 6/6.

The first prepare returned stale_selection after moving target.toml; no server was started.
The original ERROR remains saved; configuration now references the original manifest target.
This fixes campaign setup without relaxing validation or changing the core. Existing hardware scenarios
were not run in this campaign; it does not close ST-LINK GDB Server or AT32 limitations.


GitHub and prepared packages use [Hardware api040 mode](HARDWARE_CI.md#selecting-the-new-api-040-suite).

## GitHub Hardware: the new 0.4.0 suite

2026-10-10, [Hardware #13](https://github.com/ViacheslavMezentsev/stm32-gdbtest/actions/runs/38033220573), attempt 1, `codex/release-040`,
SHA `c23f8fe43ed2055e5df876b0bbd46615e69baeeb`: the GitHub API confirms success.
api040 mode: packages prepared on GitHub; runner/GDB/st-util 1.9.0 local to OrangePi.
F030R8, F103, F401CC, F411CE, F429ZI: **4 PASS + 1 expected SKIP** per board;
the TSV records doctor/hardware_exit 0/0 for every profile.

Rechecking downloaded hardware-results.zip confirmed 25 consistent JSON/JUnit outcomes, 65 records,
75 result/records/JUnit files matching indexed hashes, and verify 5/5. Generic export equals captured
records; HTML preserves PASS/SKIP separation. Every run confirms image_verified, reset_run and
shutdown_wait.ready; no capture/cleanup/teardown errors.

Warnings remain explicit: GDB 14 infers the finish stop reason (inferred_stop); the F103 profile limits
Flash to 64 KiB while the device reports 128 KiB, and the image fits both bounds.
This accepts the selected suite through GitHub, not the original ten-stage lifecycle, the entire API
or other execution layouts. The WSL2 → OrangePi/SSH result follows below.

## WSL2 → OrangePi: the new 0.4.0 suite

2026-10-10, snapshot `d1a9361`: runner in WSL2/Ubuntu 20.04, Python 3.11.16,
xPack 13.3.1-1.1 (GDB 14.2.90, embedded Python 3.11.4); st-util 1.9.0 on OrangePi over SSH.
Packages were prepared on Windows from previously checked ELF files; firmware was not rebuilt in WSL.
Source and package SHA256 hashes were retained; execution used a separate directory on the Linux filesystem.

F030R8, F103, F401CC, F411CE, F429ZI: doctor 5/5, **4 PASS + 1 expected SKIP** per board.
Total: 20 PASS, 5 SKIP (exit 77), 65 records. Independent JSON/JUnit and records digest validation passed;
export/verify/report succeeded for all five profiles. All 25 runs confirm image_verified,
reset_run, shutdown_wait.ready and remote server exit 0 / idle.ready.
No capture/cleanup/teardown errors or USB failures occurred. The existing inferred_stop and F103 Flash
capacity warnings remain; no new anomalies were found.

This verifies portable packages and the selected scenarios through WSL2 → SSH,
not a complete API or lifecycle rerun. Core and scenarios were unchanged.

## Windows: the local new 0.4.0 suite

2026-10-10, snapshot `c156db5`: Python 3.11.9, xPack 13.3.1-1.1/GDB 14.2.90,
Scoop st-util 1.9.0; runner, GDB and server local to Windows, five STM32 boards attached over USB.
The same packages as in WSL were used with matching SHA256 hashes. Doctor 5/5;
F030R8, F103, F401CC, F411CE, F429ZI — **4 PASS + 1 expected SKIP** each.
Total: 20 PASS + 5 SKIP, 65 records; JSON/JUnit and records digests checked,
export/verify/report 5/5. All 25 runs confirm image verification, reset_run and shutdown_wait.ready;
no st-util processes remain after the campaign. No USB failures occurred. Inferred_stop and F103 Flash warnings remain.

The first attempt is retained separately: 10 PASS and 5 contract preflight ERRORs before MCU connection.
GDB's embedded Python could not open an existing contract-request.json with a path longer than 260 characters;
shortening the results directory made the same packages pass completely. Original ERRORs and unavailable capture
were not relabelled PASS. [Path limitation workaround](HOWTO.md). This campaign does not establish arbitrary
long-path support; automatic early diagnostics remain a proposal.
Core and scenarios were unchanged; this is a selected new-scenario campaign, not the entire API.
