"""Explicit F0/F1/F411 experiments with prepare, baseline and restore attempts."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from stm32_gdbtest.build_manifest import digest, load_verified
from stm32_gdbtest.collect import collect
from stm32_gdbtest.backends import load_stand
from stm32_gdbtest.profile import load_profile
from stm32_gdbtest.runner import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=Path, required=True)
    parser.add_argument("--restore-session", type=Path, required=True)
    parser.add_argument("--stand", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--case", choices=("all", "techniques", "HW_E1_MEASUREMENTS", "HW_E1_ADC_PAIR", "HW_E2_READ", "HW_E3_CONTEXT", "HW_E4_FINISH"),
                        default="HW_E1_MEASUREMENTS")
    args = parser.parse_args()
    sessions = [json.loads(p.read_text(encoding="utf-8"))
                for p in (args.session, args.restore_session)]
    stand = load_stand(args.stand)
    if stand["backend"] not in ('openocd', 'jlink') or stand["flash"] != "if-different":
        raise ValueError("requires OpenOCD/J-Link with if-different")
    for session in sessions:
        load_verified(session["build_manifest"], digest(session["elf"]), session["profile"])
        if load_profile(session["profile"])["mcu"] not in ('STM32F411CEU6','STM32F030R8T6','STM32F103C8T6'):
            raise ValueError("requires a configured research board")
    if load_profile(sessions[0]['profile'])['mcu'] != load_profile(sessions[1]['profile'])['mcu']:
        raise ValueError('experiment and restore MCU differ')
    baseline_id = "HW_CI_SLEEP_SYSTICK" if args.case == "HW_E3_CONTEXT" else "HW_CI_ADC_UNITS"
    baseline = next(c for c in collect(sessions[0]["tests"]) if c["id"] == baseline_id)
    experiments = [c for c in collect(HERE / 'board')
                   if (args.case == 'all' and c['id'] in ('HW_E1_MEASUREMENTS', 'HW_E2_READ', 'HW_E3_CONTEXT', 'HW_E4_FINISH')) or c['id'] == args.case]
    baselines = [baseline]
    if args.case == 'all':
        baselines.append(next(c for c in collect(sessions[0]['tests']) if c['id'] == 'HW_CI_SLEEP_SYSTICK'))
    if args.case == 'techniques':
        native, table = {
            'STM32F030R8T6': ('HW_CI_RTC_INIT', 'HW_TECH010_F030'),
            'STM32F103C8T6': ('HW_CI_TIM2_INIT', 'HW_TECH010_F103'),
            'STM32F411CEU6': ('HW_CI_ADC_INIT', 'HW_TECH010_F411'),
        }[load_profile(sessions[0]['profile'])['mcu']]
        baselines.append(next(c for c in collect(sessions[0]['tests']) if c['id'] == native))
        cases = {c['id']: c for c in collect(HERE/'board')}
        experiments = [cases[name] for name in (table, 'HW_E1_MEASUREMENTS', 'HW_TECH011_SERIES')]
    restores = {c["id"]: c for c in collect(sessions[1]["tests"])}
    restore_ids = ('HW_BOOT','HW_GPIO') if 'HW_BOOT' in restores else ('HW_CI_BOOT','HW_CI_GPIO')
    restore_cases = [restores[name] for name in restore_ids]
    output = HERE / "build" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    output.mkdir(parents=True)
    summary = {"status": "ERROR", "stages": [], "hardware": args.execute,
               "elf_sha256": digest(sessions[0]["elf"]),
               "manifest_sha256": digest(sessions[0]["build_manifest"]),
               "restore_elf_sha256": digest(sessions[1]["elf"])}

    def execute(label, session, case, prepare=False, research=False):
        current = dict(session, root=str(HERE), out=str(output / label))
        if research:
            # Reuse the firmware's original contract registry; case path is explicit.
            current.update(root=str(HERE))
        code = run(current, case, stand_path=args.stand, prepare_only=prepare)
        paths = list((output / label).glob("*/result.json"))
        if len(paths) != 1:
            raise RuntimeError("missing unique report: " + label)
        report = json.loads(paths[0].read_text(encoding="utf-8"))
        summary["stages"].append({"label": label, "code": code, "status": report["status"],
                                  "report": str(paths[0].relative_to(output))})
        if code or report["status"] != "PASS":
            raise RuntimeError("failed stage: " + label)
        if not prepare and (not report.get("image_verified") or report.get("teardown") != "reset_run"):
            raise RuntimeError("missing verification/reset_run: " + label)

    try:
        for case in baselines:
            execute('prepare_baseline_' + case['id'], sessions[0], case, True)
        for case in experiments:
            execute('prepare_experiment_' + case['id'], sessions[0], case, True, True)
        for case in restore_cases:
            execute("prepare_restore_" + case["id"], sessions[1], case, True)
        if args.execute:
            try:
                for case in baselines:
                    execute('baseline_' + case['id'], sessions[0], case)
                for case in experiments:
                    execute('experiment_' + case['id'], sessions[0], case, research=True)
            finally:
                errors = []
                for case in restore_cases:
                    try:
                        execute("restore_" + case["id"], sessions[1], case)
                    except Exception as exc:
                        errors.append(str(exc))
                if errors:
                    raise RuntimeError("; ".join(errors))
        summary["status"] = "PASS"
    finally:
        (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(output / "summary.json", flush=True)


if __name__ == "__main__":
    main()
