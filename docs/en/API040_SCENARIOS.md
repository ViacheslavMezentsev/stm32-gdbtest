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
