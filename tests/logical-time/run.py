"""Нейтральный пример TECH-022: host и штатный Renode runner, без платы."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.collect import collect
from stm32_gdbtest.runner import run
from stm32_gdbtest.toolchain import find_gdb


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-only", action="store_true")
    parser.add_argument("--host-cxx", default="g++")
    parser.add_argument("--toolchain", type=Path)
    parser.add_argument("--renode", default="renode")
    args = parser.parse_args()
    if not args.host_only and not args.toolchain:
        parser.error("--toolchain is required for Renode")
    out = ROOT / "build/logical-time" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    inputs = out / "inputs"
    inputs.mkdir(parents=True)
    for file in Path(__file__).resolve().parent.iterdir():
        if file.is_file():
            shutil.copy2(file, inputs / file.name)
    summary = {"status": "ERROR", "mode": "host" if args.host_only else "emulator",
               "input_sha256": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in inputs.iterdir()},
               "host": [], "emulator": []}
    suffix = ".exe" if sys.platform == "win32" else ""

    def command(label, argv):
        with (out / (label + ".log")).open("w", encoding="utf-8") as log:
            proc = subprocess.run(argv, stdout=log, stderr=subprocess.STDOUT, timeout=120)
        return proc.returncode

    try:
        for defect in (0, 1, 2, 3):
            binary = out / (f"host-{defect}" + suffix)
            cmd = [args.host_cxx, "-std=c++11", "-O0", "-Wall", "-Wextra", "-Werror",
                   f"-DDEFECT={defect}", str(inputs / "model.cpp"), str(inputs / "host.cpp"), "-o", str(binary)]
            if command(f"host-build-{defect}", cmd):
                raise RuntimeError("host build failed")
            code = command(f"host-{defect}", [str(binary)])
            log = (out / f"host-{defect}.log").read_text(encoding="utf-8")
            # Негативный контроль должен упасть в ожидаемом месте, не просто вернуть ненулевой код.
            failures = [line for line in log.splitlines() if line.startswith("FAIL ")]
            expected = {0: [],
                        1: ["FAIL threshold-exact", "FAIL wrap-exact", "FAIL retry-exact"],
                        2: ["FAIL wrap-before-zero", "FAIL wrap-minus-one"],
                        3: ["FAIL retry-minus-one"]}[defect]
            ok = failures == expected and code == (1 if expected else 0)
            summary["host"].append({"defect": defect, "exit_code": code, "failures": failures, "ok": ok})
            if not ok:
                raise RuntimeError("host oracle mismatch")
        if not args.host_only:
            toolbin = args.toolchain.resolve() / "bin"
            compiler = toolbin / ("arm-none-eabi-g++" + suffix)
            gdb = find_gdb(str(toolbin / ("arm-none-eabi-gdb-py3" + suffix)))
            renode = shutil.which(args.renode) or args.renode
            for name, executable in (("gdb", gdb), ("renode", renode), ("arm", str(compiler))):
                if command(name + "-version", [executable, "--version"]):
                    raise RuntimeError(name + " version failed")
            stand = out / "stand.toml"
            stand.write_text((inputs / "stand.example.toml").read_text(encoding="utf-8")
                             .replace('executable = "renode"', "executable = " + json.dumps(Path(renode).as_posix()))
                             .replace('"platform.repl"', json.dumps((inputs / "platform.repl").as_posix())), encoding="utf-8")
            cases = {case["id"]: case for case in collect([inputs])}
            expected_cases = {"HW_EMU_TIME_THRESHOLD", "HW_EMU_TIME_WRAP", "HW_EMU_TIME_RETRY", "HW_EMU_TIME_REJECT"}
            if set(cases) != expected_cases:
                raise RuntimeError("scenario inventory mismatch")
            # Красный исход сохраняется исходным FAIL; итог кампании сравнивает его с ожиданием.
            for cycle, defect in enumerate((1, 2, 3, 0, 0)):
                elf = out / f"model-{cycle}.elf"
                cmd = [str(compiler), "-std=c++11", "-mcpu=cortex-m3", "-mthumb", "-O0", "-g3",
                       "-ffreestanding", "-nostdlib", "-fno-exceptions", "-fno-rtti", "-fno-unwind-tables",
                       "-Wl,--build-id=none", f"-DDEFECT={defect}", "-T", str(inputs / "firmware.ld"),
                       str(inputs / "model.cpp"), str(inputs / "firmware.cpp"), "-o", str(elf)]
                if command(f"arm-build-{cycle}", cmd):
                    raise RuntimeError("ARM build failed")
                for name in sorted(cases):
                    run_root = out / f"runs-{cycle}-{name}"
                    session = dict(root=str(ROOT), elf=str(elf), profile=str(inputs / "target.toml"),
                                   session_config=str(inputs / "session.toml"), gdb=gdb, out=str(run_root),
                                   stand=str(stand), tests=str(inputs))
                    if run(session, cases[name], prepare_only=True):
                        raise RuntimeError("prepare failed")
                    before = set(run_root.glob("*/result.json"))
                    code = run(session, cases[name])
                    created = set(run_root.glob("*/result.json")) - before
                    if len(created) != 1:
                        raise RuntimeError("missing or ambiguous result")
                    result_file = created.pop()
                    result = json.loads(result_file.read_text(encoding="utf-8"))
                    negative = {1: {"HW_EMU_TIME_THRESHOLD", "HW_EMU_TIME_WRAP", "HW_EMU_TIME_RETRY"},
                                2: {"HW_EMU_TIME_WRAP"}, 3: {"HW_EMU_TIME_RETRY"}}
                    expected = "FAIL" if name in negative.get(defect, set()) else "PASS"
                    record_file = result_file.parent / "records.json"
                    records = json.loads(record_file.read_text(encoding="utf-8"))["records"]
                    restored = [r for r in records if r["name"] == "restoration"]
                    failed = [c["name"] for c in result.get("checks", []) if c.get("passed") is False]
                    expected_check = {"HW_EMU_TIME_THRESHOLD": "порог включительно",
                                      "HW_EMU_TIME_WRAP": "переход через ноль",
                                      "HW_EMU_TIME_RETRY": "новая эпоха после отказа",
                                      "HW_EMU_TIME_REJECT": "отказ без изменений"}[name]
                    ok = (failed == ([expected_check] if expected == "FAIL" else [])
                          and result["status"] == expected and code == (1 if expected == "FAIL" else 0)
                          and result.get("mode") == "emulator" and result.get("cleanup") == "VERIFIED"
                          and result.get("image_verified") is True and result.get("capture", {}).get("status") == "saved"
                          and len(restored) == 1 and restored[0]["data"]["verified"] is True)
                    summary["emulator"].append(dict(cycle=cycle, defect=defect, case=name, expected=expected,
                                                    actual=result["status"], ok=ok, result=str(result_file.relative_to(out))))
                    if not ok:
                        raise RuntimeError("emulator oracle or restoration mismatch")
        summary["status"] = "PASS"
    except Exception as error:
        summary["error"] = str(error)
    finally:
        (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(out / "summary.json")
        print(summary["status"])
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
