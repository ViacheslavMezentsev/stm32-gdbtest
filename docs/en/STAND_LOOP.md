# Autonomous stand cycles

[Documentation](index.md) · [Русский](../ru/STAND_LOOP.md)

`tools/stand_loop.py` is an external 0.4.0 candidate tool. It executes an agreed finite plan through
existing CLI commands without changing Target, firmware or scenario expectations. The application
repository is not required on the stand: use this module checkout, ZIP packages, GDB-Python/binutils,
a server and a local stand TOML. No firmware build occurs on the stand.

## Bundle and plan

Prepare packages using [pack](HARDWARE_CI.md); enable `[results] capture = true` in session.toml
before packing. Add firmware sources with `--include` when needed for code analysis; scenarios,
requirements and contracts are already packaged. This does not imply a full source repository.
Package configuration is fixed; a different configuration requires a new package.

The [example plan](../../examples/stand-loop/plan.example.toml) uses our 0.4.0 scenarios.
Replace IDs and ZIP files for your application. Paths are relative to the plan; output is separate.

| Field | Value |
| --- | --- |
| schema | 1 |
| stand | local [probe] file; this first version rejects [remote] |
| cycles | 1..10000, default 1; no infinite mode |
| interval_s | delay between cycles 0..86400, default 0 |
| on_fail | stop (default) or continue; applies only to a confirmed scenario FAIL |
| min_free_mib | minimum free space 1..1048576, default 256 MiB |
| cases | ordered list of 1..64 entries |
| cases.package / id | ZIP and an ID from its manifest |
| cases.allow_skip | bool, default false; permits SKIP but does not require it |
| cases.timeout_s | 1..3600, default 60; runner GDB timeout, not an overall campaign deadline |

Unknown fields and invalid types are rejected. Package and module versions must match; every
package must enable capture. Copies of packages/stand/plan, input hashes and module/dispatcher
Python hashes are retained. Inputs and code are checked between operations; do not edit them
concurrently. This checks reproducibility, not isolation from untrusted Python scenarios.

## Run on OrangePi

```sh
. "$HOME/.local/stm32-gdbtest/env.sh"
cd "$HOME/stm32-gdbtest"
python3 -B tools/stand_loop.py --plan "$HOME/stand/plan.toml" --output "$HOME/stand/runs/run-001"
```

Output must be new; retries never overwrite an earlier campaign. Doctor runs first, then every
selected scenario is prepared before any MCU access. Any preparation failure prevents hardware
execution. Each run checks identity/package/exit/status, verified image, reset_run, capture/records/
JUnit and, for st-util, shutdown_wait.ready. Application expectations remain in the scenario;
PASS does not establish that its checks are complete.

| Outcome | Continuation and dispatcher exit |
| --- | --- |
| PASS, permitted SKIP | next scenario; completed plan exits 0 |
| FAIL | stop: exit 1; continue: further cases run, final exit remains 1 |
| ERROR, unexpected SKIP, inconsistent/missing artifacts | stop with 2 |
| All-SKIP cycle | nothing tested, stop with 2 |
| Export/verify/report error or changed inputs | stop with 2; original statuses retained |
| STOP or SIGINT/SIGTERM | finish current command and evidence processing, then stop with 130 |

Scenario counts remain separate. COMPLETED means the plan completed, not a new PASS verdict or
whole-device acceptance. UNKNOWN and processing code 2 cannot be hidden by successful HTML output.
The dispatcher does not retry ERRORs or independently recover hardware; normal cleanup belongs
to the runner. USB failures may require manual intervention.

Create an empty `<output>/STOP` for an orderly stop. It does not interrupt the current command;
do not remove locks or kill the server instead of waiting for cleanup. A separate temporary
family/serial lock prevents two stand_loop processes from using the same debugger. After a crash,
the lock remains: confirm the owner and its children have ended before removal. The normal runner
lock protects each attempt; other manual tools are not excluded between attempts by the dispatcher.

## Artifacts and the agent

```text
run-001/
  plan.toml, inputs.json, inputs/   input snapshot and hashes (stand contains personal settings)
  doctor.log, prepare/             environment and offline preflight
  summary.json                    campaign state, separate counters, exit code
  c00001/
    t000/, t001/                  separate extracted packages and primary results
    selection.json, summary.json  exact selection and cycle state
    export/, integrity.json       journal and file verification
    report/                       campaign.json/html
    review.json                   published last: cycle ready for review
```

The agent reads cycles with review.json only; an unfinished cycle has none. Partial cycles retain
all available results, processing errors and the stop reason. Scenario sources are available in
extracted packages under tNNN. The selection root is cNNNNN.
[stm32-gdbtest-results](../../skills/stm32-gdbtest-results/SKILL.md) explains interpretation;
[stm32-gdbtest-stand-loop](../../skills/stm32-gdbtest-stand-loop/SKILL.md) explains operation.

The dispatcher does not invoke pi/Qwen or execute commands from their replies. An external agent
can watch for new review.json files and write separate assessments and proposals. It must not
automatically change plans, expectations or packages, or resume a failed campaign. Firmware source
snapshots for causal analysis are optional additional inputs; absent sources limit conclusions.

## Background service and initial limits

The [user systemd template](../../examples/stand-loop/stand-loop@.service) runs one finite plan.
Check checkout, env.sh, plan paths and USB access before installation. After review:

```sh
mkdir -p "$HOME/.config/systemd/user"
cp examples/stand-loop/stand-loop@.service "$HOME/.config/systemd/user/"
systemctl --user daemon-reload
systemctl --user start stand-loop@run-001
journalctl --user -u stand-loop@run-001
```

Use a fresh instance/output for each campaign. Restart=no prevents automatic retry after ERROR.
`systemctl --user stop` requests dispatcher shutdown after the current command; the unit does not
SIGKILL its children. Operation after logout requires a configured user manager/linger, an explicit
administrator setup step that the tool does not perform.

The first version does not promise 24/7 operation, power-loss durability, disk cleanup, a whole-process
deadline, USB repair, automatic package deployment or a secure LLM sandbox. If the host CLI itself
hangs, orderly STOP also waits; an external automatic watchdog is not implemented. Free-space checks
before steps do not reserve disk space or replace quotas. A manual hardware run does not verify
the service or model integration.

## Initial verification — 2026-10-10

StandLoopTests: 20 host checks covering doctor/prepare gates, FAIL stop/continue, permitted and
unexpected SKIP, all-SKIP cycles, corrupt records/JUnit, wrong package/mode/code, cleanup/capture,
changed inputs, occupied locks, STOP, low disk space and evidence processing failure.

Hardware: F411CE/ST-Link, local OrangePi 5/Ubuntu 20.04 aarch64, Python 3.11.16,
xPack 13.3.1-1.1/GDB 14.2.90 and st-util 1.9.0. Unchanged 0.4.0 scenario packages were used:

| Plan | Actual result |
| --- | --- |
| 2 RECORDS + permitted-SKIP cycles | COMPLETED/code0, 2 PASS + 2 SKIP, two separate reviews |
| 3 cycles, STOP after first review | STOPPED/code130, 1 PASS + 1 SKIP; no second cycle directory |
| 2 cycles without SKIP permission | ERROR/code2 after the first SKIP; no repeat |

Total: 7 hardware runs, 3 PASS + 4 SKIP, 20 records. In the last plan SKIP remains the scenario
outcome while ERROR is the dispatcher decision. All 7 images/teardown/shutdown_wait are confirmed;
export/verify/report succeeded for 4 cycles, fresh copied-evidence verification 4/4.
Input/runtime hashes matched; no st-util processes or dispatcher locks remained.
The finish inferred_stop warning was retained. No hardware fault was deliberately induced.

The first SSH shell wrapper received a trailing CR after Python completed successfully and returned
an error; its summary and evidence were retained. Later checks ran from a transferred LF script
and checked actual exits 130/2. This is not an MCU error or a reason to rewrite the original record.
The systemd template passed `systemd-analyze --user verify` but was not installed or started.
pi/Qwen were not invoked; this stage does not accept model integration, long-duration runs or other boards.
