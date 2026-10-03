"""Hardware validation of the CI firmware on a local Windows or Linux stand (development, not CI).

Builds one CI profile, then runs the scenarios through the real runner and GDB server
and checks the expected outcome of each step:

  build            configure, build, CTest host label (traceability, prepare.<ID>)
  prepare          run --prepare-only with the stand (backend commands, J-Link mapping)
  boot             HW_CI_BOOT, programs Flash if the image differs
  gpio             HW_CI_GPIO, no reprogramming expected
  strict           HW_CI_BOOT with --identity-policy strict, DEV_ID must match
  full-a5          full 16 KiB image with fill 0xA5, programmed and verified with CRC
  verify-only-ff   fill 0xFF with flash=verify-only: expected ERROR, nothing written
  full-ff          fill 0xFF with if-different: restores the erased tail
  timeout          HW_CI_BOOT with a 0.2 s GDB deadline: expected ERROR and host recovery
  after-recovery   HW_CI_GPIO passes again after recovery

The test boards are reprogrammed: use only boards agreed for experiments.
Usage (repository root; on Linux first `. ~/.local/stm32-gdbtest/env.sh`, see tools/linux_stand.py):
  python -B tests/firmware/run_hw.py --profile f411ce --stand tests/firmware/stands/f411ce-openocd.local.toml
Results: build/hw/<profile>-<stand name>/summary.json and the runner reports it lists.

A package from `python -m stm32_gdbtest pack` replaces the build here (--package; built and
prepared elsewhere, e.g. in CI). --repeat N repeats the steps (0: until Ctrl+C) and writes
soak.json with counters plus iterations/NNNNN.json (docs/en/HARDWARE_CI.md).
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import zipfile

if sys.version_info < (3, 11):
    sys.exit(f"run_hw.py needs Python 3.11+, this is {sys.version.split()[0]}. "
             "On a Linux stand run: . ~/.local/stm32-gdbtest/env.sh")
import tomllib  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
FIRMWARE = ROOT / "tests/firmware"
STEPS = ("build", "prepare", "boot", "gpio", "strict", "full-a5", "verify-only-ff", "full-ff", "timeout",
         "after-recovery")


class StepError(RuntimeError):
    pass


def command(args, log, env, timeout=900):
    started = time.monotonic()
    result = subprocess.run([str(a) for a in args], cwd=ROOT, env=env, timeout=timeout, text=True,
                            errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with open(log, "a", encoding="utf-8") as stream:
        stream.write(f"$ {' '.join(map(str, args))}\n{result.stdout}\n[exit {result.returncode}, "
                     f"{time.monotonic() - started:.1f}s]\n\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", required=True, choices=("f030r8", "f103c8", "f411ce"))
    parser.add_argument("--stand", required=True, type=Path, help="local stand TOML ([probe] table)")
    # Windows keeps the historical per-user defaults; Linux takes them from env.sh.
    home = Path(os.environ["USERPROFILE"]) if os.name == "nt" else None
    parser.add_argument("--toolchain", type=Path, default=os.environ.get("ARM_TOOLCHAIN_ROOT")
                        or (home / "xpack-arm-none-eabi-gcc-13.3.1-1.1" if home else None))
    parser.add_argument("--cube", type=Path, default=os.environ.get("STM32CUBE_REPOSITORY")
                        or (home / "STM32Cube/Repository" if home else None))
    parser.add_argument("--steps", nargs="*", choices=STEPS, default=list(STEPS))
    parser.add_argument("--package", type=Path,
                        help="prepared run package from `pack`: no build here, the build step checks the package")
    parser.add_argument("--repeat", type=int, default=1,
                        help="repeat the steps N times (0: until interrupted); build runs only once")
    args = parser.parse_args()
    if args.repeat < 0:
        sys.exit("--repeat must be 0 (until interrupted) or a positive number")
    if not args.package and (not args.toolchain or not args.cube):
        sys.exit("Set ARM_TOOLCHAIN_ROOT and STM32CUBE_REPOSITORY (source env.sh of tools/linux_stand.py) "
                 "or pass --toolchain and --cube")
    stand_path = args.stand.resolve()
    document = tomllib.loads(stand_path.read_text(encoding="utf-8"))
    probe = document["probe"]
    name = f"{args.profile}-{stand_path.name.split('.')[0]}"
    build = FIRMWARE / "build" / f"hw-{name}"
    out = ROOT / "build/hw" / name
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    log = out / "run_hw.log"
    env = dict(os.environ, ARM_TOOLCHAIN_ROOT=str(args.toolchain), STM32CUBE_REPOSITORY=str(args.cube),
               PYTHONDONTWRITEBYTECODE="1")
    for variable in ("STM32_GDBTEST_STAND", "STM32_GDBTEST_IMAGE_POLICY", "STM32_GDBTEST_IDENTITY_POLICY"):
        env.pop(variable, None)
    session = build / "hwtest/session.json"
    cli = [sys.executable, "-B", ROOT / "stm32_gdbtest/cli.py", "run", "--session", session]
    runs = build / "hwtest/runs"
    if args.package:
        package = args.package.resolve()
        if not package.is_file():
            sys.exit(f"Package not found: {package} (copy it to this computer first)")
        workdir = out / "package"
        cli = [sys.executable, "-B", ROOT / "stm32_gdbtest/cli.py", "run", "--package", package,
               "--workdir", workdir]
        runs = workdir / hashlib.sha256(package.read_bytes()).hexdigest()[:16]
    policy = FIRMWARE / f"profiles/{args.profile}/full-image.toml"
    policy_a5 = out / "full-image-a5.toml"
    policy_a5.write_text(policy.read_text(encoding="utf-8").replace("fill = 255", "fill = 165"), encoding="utf-8")
    stand_verify = out / "stand-verify-only.toml"
    tables = dict(document, probe=dict(probe, flash="verify-only"))  # keeps [remote] of a remote stand
    stand_verify.write_text("".join(f"[{table}]\n" + "".join(f"{key} = {json.dumps(value)}\n"
                                                             for key, value in values.items())
                                    for table, values in tables.items()), encoding="utf-8")
    def scenario(test_id, *extra, stand=stand_path, image_policy=None, expect=0):
        run_env = dict(env, STM32_GDBTEST_IMAGE_POLICY=str(image_policy)) if image_policy else env
        selected_cli = cli
        selected_runs = runs
        if image_policy:
            # Separate legacy-image descriptor deliberately tests the old interface.
            if args.package:
                sys.path.insert(0, str(ROOT))
                from stm32_gdbtest.package import open_package
                data = open_package(package, workdir)
                selected_runs = Path(data['out'])
            else:
                data = json.loads(session.read_text(encoding='utf-8'))
            data.pop('session_config', None)
            data.pop('_config_capsule', None)
            legacy = out / 'session-legacy-image.json'
            legacy.write_text(json.dumps(data), encoding='utf-8')
            selected_cli = [sys.executable, '-B', ROOT / 'stm32_gdbtest/cli.py', 'run', '--session', legacy]
        result = command([*selected_cli, "--test", test_id, "--stand", stand, *extra], log, run_env)
        reports = sorted(selected_runs.glob(f"**/*-{test_id}-*/result.json"), key=lambda p: p.stat().st_mtime)
        report = json.loads(reports[-1].read_text(encoding="utf-8")) if reports else {}
        if result.returncode != expect:
            raise StepError(f"exit {result.returncode}, expected {expect}: {report.get('error', result.stdout[-2000:])}")
        return report, reports[-1] if reports else None

    def require(condition, message):
        if not condition:
            raise StepError(message)

    def step_build():
        if args.package:
            # ТЗ 5.19: the package was built and prepared elsewhere; check it holds the CI scenarios.
            with zipfile.ZipFile(args.package) as bundle:
                manifest = json.loads(bundle.read("ddtt-package.json"))
            ids = {test["id"] for test in manifest["tests"]}
            require({"HW_CI_BOOT", "HW_CI_GPIO"} <= ids, f"package lacks CI scenarios: {sorted(ids)}")
            return None, None
        configure = command(["cmake", "-S", FIRMWARE, "-B", build, "-G", "Ninja", "--toolchain",
                             FIRMWARE / "cmake/arm-gcc.cmake", f"-DCI_PROFILE={args.profile}",
                             f"-DARM_TOOLCHAIN_ROOT={args.toolchain}", f"-DSTM32CUBE_REPOSITORY={args.cube}",
                             "-DCMAKE_BUILD_TYPE=Debug", "-DSTM32_GDBTEST_STAND="], log, env)
        require(configure.returncode == 0, "configure failed; see run_hw.log")
        require(command(["cmake", "--build", build], log, env).returncode == 0, "build failed; see run_hw.log")
        ctest = command(["ctest", "--test-dir", build, "-L", "host", "--output-on-failure"], log, env)
        require(ctest.returncode == 0, "CTest host label failed; see run_hw.log")
        return None, None

    def step_prepare():
        report, path = scenario("HW_CI_BOOT", "--prepare-only")
        require(report.get("backend_commands"), "stand backend commands missing")
        return report, path

    def step_boot():
        report, path = scenario("HW_CI_BOOT")
        require(report.get("image_verified") is True, "image not verified")
        require(report.get("teardown") == "reset_run", f"teardown {report.get('teardown')}")
        return report, path

    def step_gpio():
        report, path = scenario("HW_CI_GPIO")
        require(report.get("flashed") is False, "Flash reprogrammed although the image matched")
        return report, path

    def step_strict():
        report, path = scenario("HW_CI_BOOT", "--identity-policy", "strict")
        require(report.get("identity", {}).get("matches") is True, "DEV_ID does not match the profile")
        return report, path

    def step_full_a5():
        report, path = scenario("HW_CI_GPIO", image_policy=policy_a5)
        verification = report.get("image_verification", {})
        require(report.get("flashed") is True, "A5 tail was not programmed")
        require(verification.get("full_region_crc_verified") is True, "full image CRC not verified")
        return report, path

    def step_verify_only_ff():
        report, path = scenario("HW_CI_GPIO", stand=stand_verify, image_policy=policy, expect=2)
        require(report.get("flashed") is False, "verify-only wrote Flash")
        require(report.get("image_verification", {}).get("bytes_match") is False, "A5 tail not detected")
        return report, path

    def step_full_ff():
        report, path = scenario("HW_CI_GPIO", image_policy=policy)
        require(report.get("flashed") is True, "FF tail was not restored")
        require(report.get("image_verification", {}).get("full_region_crc_verified") is True, "CRC not verified")
        return report, path

    def step_timeout():
        report, path = scenario("HW_CI_BOOT", "--timeout", "0.2", expect=2)
        require(report.get("teardown") == "reset_run (host recovery)", f"teardown {report.get('teardown')}")
        return report, path

    def step_after_recovery():
        return scenario("HW_CI_GPIO")

    handlers = {"build": step_build, "prepare": step_prepare, "boot": step_boot, "gpio": step_gpio,
                "strict": step_strict, "full-a5": step_full_a5, "verify-only-ff": step_verify_only_ff,
                "full-ff": step_full_ff, "timeout": step_timeout, "after-recovery": step_after_recovery}
    def iteration(first):
        results = []
        for step in [s for s in STEPS if s in args.steps and (first or s != "build")]:
            started = time.monotonic()
            try:
                report, path = handlers[step]()
                status, detail = "PASS", None
            except Exception as error:  # the next steps still run and report their own state
                status, detail, report, path = "FAIL", str(error), None, None
            entry = dict(step=step, status=status, seconds=round(time.monotonic() - started, 1), detail=detail,
                         report=str(path.relative_to(ROOT)) if path else None)
            if report:
                entry.update(result=report.get("status"), flashed=report.get("flashed"),
                             teardown=report.get("teardown"), warnings=report.get("warnings"),
                             backend_version=report.get("compatibility", {}).get("backend", {}).get("version"),
                             debugger_firmware=report.get("compatibility", {}).get("debugger", {}).get("firmware"))
            results.append(entry)
            print(f"{status} {step} ({entry['seconds']}s)" + (f": {detail}" if detail else ""), flush=True)
        return dict(schema=1, profile=args.profile, backend=probe.get("backend"), stand=stand_path.name,
                    server_host=document.get("remote", {}).get("host", "local"),
                    host=f"{platform.system()} {platform.release()} {platform.machine()}",
                    toolchain=None if args.package else str(args.toolchain),
                    package=args.package.name if args.package else None,
                    passed=sum(r["status"] == "PASS" for r in results), total=len(results), steps=results)

    if args.repeat == 1:
        summary = iteration(True)
        (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{summary['passed']}/{summary['total']} steps passed; {out / 'summary.json'}")
        return 0 if summary["passed"] == summary["total"] else 1
    # Soak mode (ТЗ 5.20): repeat until N iterations or Ctrl+C; every iteration keeps its summary.
    soak = dict(schema=1, profile=args.profile, stand=stand_path.name, repeat=args.repeat,
                started_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), iterations=0,
                passed_iterations=0, step_failures={}, first_failure=None, last_utc=None, interrupted=False)
    (out / "iterations").mkdir()
    number = 0
    try:
        while args.repeat == 0 or number < args.repeat:
            number += 1
            print(f"--- iteration {number}", flush=True)
            summary = iteration(number == 1)
            (out / "iterations" / f"{number:05d}.json").write_text(json.dumps(summary, indent=2) + "\n",
                                                                     encoding="utf-8")
            soak["iterations"] = number
            soak["last_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            if summary["passed"] == summary["total"]:
                soak["passed_iterations"] += 1
            for entry in summary["steps"]:
                if entry["status"] != "PASS":
                    soak["step_failures"][entry["step"]] = soak["step_failures"].get(entry["step"], 0) + 1
                    soak["first_failure"] = soak["first_failure"] or dict(iteration=number, step=entry["step"],
                                                                          detail=entry["detail"])
            (out / "soak.json").write_text(json.dumps(soak, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except KeyboardInterrupt:
        soak["interrupted"] = True
        (out / "soak.json").write_text(json.dumps(soak, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{soak['passed_iterations']}/{soak['iterations']} iterations passed; {out / 'soak.json'}")
    return 0 if soak["iterations"] and soak["passed_iterations"] == soak["iterations"] else 1

if __name__ == "__main__":
    sys.exit(main())
