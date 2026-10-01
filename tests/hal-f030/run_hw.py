"""Explicit F030/OpenOCD acceptance via CLI; always attempts original firmware restore."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
MODULE = ROOT.parents[1]
sys.path.insert(0, str(MODULE))
from stm32_gdbtest.build_manifest import digest, load_verified
from stm32_gdbtest.collect import collect
from stm32_gdbtest.openocd import load_stand
from stm32_gdbtest.profile import load_profile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stand", required=True, type=Path)
    parser.add_argument("--restore-session", required=True, type=Path)
    args = parser.parse_args()
    stand = args.stand.resolve()
    config = load_stand(stand)
    if config["backend"] != "openocd" or config["flash"] != "if-different":
        raise ValueError("This protocol requires OpenOCD and if-different restoration")
    session_path = ROOT / "build/debug/hwtest/session.json"
    restore_path = args.restore_session.resolve()
    sessions = [json.loads(p.read_text(encoding="utf-8")) for p in (session_path, restore_path)]
    # Validate both manifests and MCU before the first server, including the restore image.
    for session in sessions:
        load_verified(session["build_manifest"], digest(session["elf"]), session["profile"])
        if load_profile(session["profile"])["mcu"] != "STM32F030R8T6":
            raise ValueError("Both sessions must target STM32F030R8T6")
    cases = collect(sessions[0]["tests"])
    if len(cases) != 22:
        raise ValueError("Expected 22 HAL scenarios")
    restore_ids = {c["id"] for c in collect(sessions[1]["tests"])}
    if not {"HW_BOOT", "HW_BLINK"}.issubset(restore_ids):
        raise ValueError("Restore session needs boot and blink checks")
    out = ROOT / "build/validation" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    out.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("STM32_GDBTEST_", "HWTEST_")) and k not in ("PYTHONHOME", "PYTHONPATH")}
    env.update(PYTHONDONTWRITEBYTECODE="1", TEMP=str(out), TMP=str(out))
    summary = dict(status="ERROR", firmware_sha256=digest(sessions[0]["elf"]),
                   restore_sha256=digest(sessions[1]["elf"]), stages=[])

    def execute(label, path, identifier, timeout=None, expect=0):
        data = json.loads(path.read_text(encoding="utf-8"))
        runs = Path(data.get("out", Path(data["elf"]).parent / "hwtest/runs"))
        before = set(runs.glob("*/result.json"))
        cmd = [sys.executable, "-B", str(MODULE / "stm32_gdbtest/cli.py"), "run",
               "--session", str(path), "--test", identifier, "--stand", str(stand)]
        if timeout is not None:
            cmd += ["--timeout", str(timeout)]
        with (out / f"{label}.log").open("wb") as log:
            result = subprocess.run(cmd, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        fresh = set(runs.glob("*/result.json")) - before
        if len(fresh) != 1:
            raise RuntimeError(f"{label}: expected one new report, got {len(fresh)}")
        report_path = fresh.pop()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        summary["stages"].append(dict(label=label, code=result.returncode,
                                     report=str(report_path), status=report["status"],
                                     teardown=report.get("teardown")))
        print(label, report["status"], flush=True)
        if result.returncode != expect or report["status"] != ("PASS" if expect == 0 else "ERROR"):
            raise RuntimeError(f"Unexpected result for {label}: {report_path}")
        if expect == 0 and (not report.get("image_verified") or report.get("teardown") != "reset_run"):
            raise RuntimeError("Missing image verification or reset_run: " + label)
        return report, report_path.parent

    try:
        for case in cases:
            execute(case["id"], session_path, case["id"])
            if case["id"] in ("HW_ADC_START_ERROR", "HW_ADC_DMA_TIMEOUT", "HW_RCC_ERROR",
                              "HW_RCC_OSC_NULL", "HW_RCC_CLOCK_NULL"):
                for positive in ("HW_ADC_DMA_RUNTIME", "HW_TIM3_IRQ", "HW_RTC_ALARM"):
                    execute(case["id"] + "_after_" + positive, session_path, positive)
        # Host timeout/recovery is separate from application error injection.
        tests = out / "timeout-tests"
        tests.mkdir()
        (tests / "test_timeout.py").write_text(
            'from stm32_gdbtest import case\nimport os, time, json\nfrom pathlib import Path\n'
            '@case("HW_HAL_TIMEOUT", timeout_s=5)\n'
            'def stall(t):\n'
            '    t.reach("loop")\n'
            '    request = json.loads(Path(os.environ["STM32_GDBTEST_RUN"]).read_text())\n'
            '    Path(request["result"]).with_name("stall-entered.txt").write_text("at loop")\n'
            '    time.sleep(60)\n', encoding="utf-8")
        injected = out / "timeout-session.json"
        injected.write_text(json.dumps(dict(sessions[0], tests=str(tests))), encoding="utf-8")
        report, run_dir = execute("timeout", injected, "HW_HAL_TIMEOUT", timeout=5, expect=2)
        if (not (run_dir / "stall-entered.txt").exists()
                or "TimeoutExpired" not in report.get("error", "")
                or report.get("teardown") != "reset_run (host recovery)"):
            raise RuntimeError("Timeout did not exercise entered scenario and host recovery")
        execute("after_recovery", session_path, "HW_ADC_DMA_RUNTIME")
        summary["status"] = "PASS"
    except BaseException as error:
        summary["error"] = str(error)
        raise
    finally:
        try:
            for identifier in ("HW_BOOT", "HW_BLINK"):
                execute("restore_" + identifier, restore_path, identifier)
            summary["restored"] = True
        except BaseException as error:
            summary.update(status="ERROR", restored=False, restore_error=str(error))
            raise
        finally:
            (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
            print("Evidence:", out, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
