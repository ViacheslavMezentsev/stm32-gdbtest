"""Explicit F411 E1 run with prepare, baseline and unconditional restore attempt."""

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
    parser.add_argument("--case", choices=("HW_E1_MEASUREMENTS", "HW_E1_ADC_PAIR", "HW_E2_READ", "HW_E3_CONTEXT"),
                        default="HW_E1_MEASUREMENTS")
    args = parser.parse_args()
    sessions = [json.loads(p.read_text(encoding="utf-8"))
                for p in (args.session, args.restore_session)]
    stand = load_stand(args.stand)
    if stand["backend"] != "openocd" or stand["flash"] != "if-different":
        raise ValueError("requires OpenOCD with if-different")
    for session in sessions:
        load_verified(session["build_manifest"], digest(session["elf"]), session["profile"])
        if load_profile(session["profile"])["mcu"] != "STM32F411CEU6":
            raise ValueError("requires F411CE images")
    baseline_id = "HW_CI_SLEEP_SYSTICK" if args.case == "HW_E3_CONTEXT" else "HW_CI_ADC_UNITS"
    baseline = next(c for c in collect(sessions[0]["tests"]) if c["id"] == baseline_id)
    experiment = next(c for c in collect(HERE / "board") if c["id"] == args.case)
    restores = {c["id"]: c for c in collect(sessions[1]["tests"])}
    restore_cases = [restores[name] for name in ("HW_BOOT", "HW_GPIO")]
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
        execute("prepare_baseline", sessions[0], baseline, True)
        execute("prepare_experiment", sessions[0], experiment, True, True)
        for case in restore_cases:
            execute("prepare_restore_" + case["id"], sessions[1], case, True)
        if args.execute:
            try:
                execute("baseline", sessions[0], baseline)
                execute("experiment", sessions[0], experiment, research=True)
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
