# Joint capture with a synthetic external source

[Русский](README.md) · [TECH-026](../../docs/en/TESTING_TECHNIQUES.md#tech-026)

Standalone host example, no MCU/GDB/Renode or core changes. The scenario is explicitly
a host fixture, not an executed module @case. A separate Python source receives only
run/revision and emits its predefined stream without reading the scenario result.
Both streams are synthetic: this validates correlation/delivery, not sensor accuracy.

The coordinator waits for READY (3 s), opens the window, saves the host scenario result,
drains the stream through EOF and waits for exit (2 s capture phase). On timeout it
kills only its own process, waits for its reader and saves raw bytes/stderr/exit code.
The fixture source has no descendants. COMPLETE means transport EOF and exit 0;
application completeness still requires an end marker, exact channels, count and order.
No READY means NOT_RUN. A post-window capture failure can leave scenario PASS unchanged.

Expected signal/unit records have sequences 0/1/2 and values 10/20/30. Scenario ticks
10/20/30 correspond to source ticks 1010/1020/1030. Two fixture-defined anchors
(0,1000), (40,1040) establish offset=1000 with uncertainty ±1 and tolerance ±2 ticks.
These are model assumptions, not measured clock synchronization. Host monotonic time
only checks readiness/window/closure order, not source event timing. A whole uncertainty
interval inside tolerance passes; wholly outside fails; overlap gives UNKNOWN.
Unqualified clocks block dependent comparisons. Real adapters need proven anchors,
drift, units, epoch and clock resolution; do not fit clocks to the desired result.

Nineteen cases produce two PASS, two FAIL and fifteen UNKNOWN analysis verdicts.
Missing/duplicate/reordered/corrupt records, mismatched identity/units/channels, missing
end markers, unusable clocks and time-boundary overlap yield UNKNOWN. Complete valid
records contradicting value or timing expectations yield FAIL while scenario stays PASS.
A failed host scenario remains FAIL. A normal repeat after all fault cases checks reuse.
Campaign success requires exact verdicts/reasons, preserved scenario and verified cleanup.

Run `python tests/external-capture/run.py` (Python 3.11+, no third-party dependencies).
Optional --output requires a new directory. Default artifacts: build/external-capture.
Reanalyze without source: `python tests/external-capture/analysis.py <case-directory>`.
Analysis exits 0/1/2 for PASS/FAIL/UNKNOWN; campaign exit 0 means the expected matrix.
Each case retains manifest/scenario/capture/analysis JSON, external.jsonl, stderr and
SHA-256. These are fixture formats, not new module result/records schemas. Reanalysis
checks hashes when present and never rewrites the scenario. Hashes detect changes,
not authenticity against simultaneous replacement of data and hash manifest.

Keep subprocess/pipe waits outside GDB's main thread. Receiver readiness must precede
resume(sync=False); await wait/halt controls the target, not capture completeness.
Drain remains necessary. record links external identity/hash/epoch; it does not import
external files, and runtime records need capture=true to persist. Missing data is
UNKNOWN analysis, not zero or skip hiding a failure. Gate only dependent DDTT claims.
ROS/rosbag, Android MCAP and radio-emulator adapters remain future work. No hardware
recovery, GDB live-window, physical qualification or real-container acceptance is claimed.

Validated 2026-10-27 on Windows/Linux: 19/19 expected outcomes, including a repeat
after faults and verified cleanup. Regressions cover full uncertainty intervals,
readiness, input immutability and hash-based tamper detection. The host scenario checks
three scaled inputs against explicit expectations; its own failed check is preserved
and gates analysis, without claiming hardware failure.
