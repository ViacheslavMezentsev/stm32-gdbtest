"""Offline CI checks of stm32-gdbtest: everything up to the GDB server, no debugger.

Levels (spec 8.11):
  docs      specification consistency, local Markdown links, RU/EN documentation pairs
  format    C/C++ sources match .clang-format (clang-format --dry-run --Werror)
  host      module host tests (unittest)
  hal       F030 HAL GCC13: build, exact 19 CTest checks, prepare JSON, negative contracts
  firmware  CI firmware per GCC x profile: configure, build, build manifest, CTest host
            tests (traceability, prepare with offline contracts), full-image prepare,
            negative contract and image-policy cases

Usage inside the CI image (see docs/ru/testing.md):
  python3 ci/run_checks.py [docs] [format] [host] [firmware] [hal] [--gcc VERSION ...] [--profile NAME ...]
Without levels all of them run. Results: build/ci/summary.json.
"""

import argparse
import copy
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "ci/dependencies.lock.json").read_text(encoding="utf-8"))
FIRMWARE = ROOT / "tests/firmware"
OUT = ROOT / "build/ci"
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.contracts import select_contracts  # noqa: E402
from stm32_gdbtest.image import parse_sections  # noqa: E402


class CheckError(RuntimeError):
    pass


def run(args, *, cwd=ROOT, env=None, expect=0, timeout=600, log=None):
    """Run a command, keep its output in the log file and require the exit code."""
    started = time.monotonic()
    result = subprocess.run([str(a) for a in args], cwd=cwd, env=env, timeout=timeout,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace")
    if log:
        with open(log, "a", encoding="utf-8") as stream:
            stream.write(f"$ {' '.join(map(str, args))}\n{result.stdout}\n[exit {result.returncode}, "
                         f"{time.monotonic() - started:.1f}s]\n\n")
    if result.returncode != expect:
        tail = "\n".join(result.stdout.splitlines()[-30:])
        raise CheckError(f"{' '.join(map(str, args))}: exit {result.returncode}, expected {expect}\n{tail}")
    return result.stdout


# --- docs -----------------------------------------------------------------------------------

LINK = re.compile(r"\]\(([^)\s]+)\)")


def check_links():
    broken = []
    for path in sorted(ROOT.rglob("*.md")):
        if any(part in ("build", ".git") for part in path.relative_to(ROOT).parts):
            continue
        for target in LINK.findall(path.read_text(encoding="utf-8")):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            if not (path.parent / target.split("#", 1)[0]).exists():
                broken.append(f"{path.relative_to(ROOT)} -> {target}")
    if broken:
        raise CheckError("Broken local links:\n" + "\n".join(broken))


def check_pairs():
    ru = {p.name for p in (ROOT / "docs/ru").glob("*.md")}
    en = {p.name for p in (ROOT / "docs/en").glob("*.md")}
    missing = sorted(f"docs/en/{n}" for n in ru - en) + sorted(f"docs/ru/{n}" for n in en - ru)
    for base in ("README", "CHANGELOG"):
        if not ((ROOT / f"{base}.md").exists() and (ROOT / f"{base}.en.md").exists()):
            missing.append(f"{base}.md / {base}.en.md")
    # Spec 7.7.13: every page links its language's map and the same page in the other language.
    for lang, other in (("ru", "en"), ("en", "ru")):
        for page in sorted((ROOT / "docs" / lang).glob("*.md")):
            head = "\n".join(page.read_text(encoding="utf-8").splitlines()[:4])
            if f"(../{other}/{page.name})" not in head or (page.name != "index.md" and "(index.md)" not in head):
                missing.append(f"navigation line in docs/{lang}/{page.name}")
    if missing:
        raise CheckError("Missing RU/EN pair: " + ", ".join(missing))


def level_docs(record):
    check_spec = os.environ.get("CHECK_SPEC")
    if not check_spec or not Path(check_spec).is_file():
        raise CheckError("Set CHECK_SPEC to embedded-tech-spec/scripts/check_spec.py (preinstalled in the CI image)")
    record("docs.spec", lambda: run([sys.executable, check_spec, ROOT / "docs/TECHNICAL_SPECIFICATION.md", "--strict"]))
    record("docs.links", check_links)
    record("docs.pairs", check_pairs)


# --- format ---------------------------------------------------------------------------------

def level_format(record):
    def check():
        sources = [p for p in sorted(ROOT.rglob("*")) if p.suffix in (".c", ".h", ".cpp", ".hpp")
                   and not any(part in ("build", ".git") for part in p.relative_to(ROOT).parts)
                   # Preserve imported CubeMX and platform code; check owned application sources.
                   and not p.is_relative_to(ROOT / "tests/hal-f030/Core")
                   and p != ROOT / "tests/hal-f030/src/platform.c"]
        run(["clang-format", "--dry-run", "--Werror", *sources], log=OUT / "format.log")
        return f"{len(sources)} files"
    record("format.clang-format", check)


# --- host -----------------------------------------------------------------------------------

def level_host(record):
    record("host.unittest", lambda: run([sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests/host", "-v"],
                                        log=OUT / "host.log"))


# --- firmware -------------------------------------------------------------------------------

NEGATIVE_CONTRACTS = {
    "missing_macro": lambda c: c["ci_gpio_macros"]["macros"]["expressions"].append("MISSING_CI_MACRO"),
    "wrong_macro_context": lambda c: c["ci_gpio_macros"]["macros"].update(context="missing_context"),
    "wrong_return_type": lambda c: c["ci_app_api"]["functions"]["app_step"].update(returns="uint8_t"),
    "wrong_argument_name": lambda c: c["ci_app_api"]["functions"]["app_step"]["arguments"][0].update(name="st"),
    "wrong_argument_type": lambda c: c["ci_app_api"]["functions"]["app_step"]["arguments"][1].update(type="uint32_t"),
    "wrong_arity": lambda c: c["ci_app_api"]["functions"]["app_loop"]["arguments"].append(
        dict(name="value", type="uint32_t")),
    "wrong_field_type": lambda c: c["ci_app_api"]["fields"]["app_state_t"].update(led="uint32_t"),
    "missing_field": lambda c: c["ci_app_api"]["fields"]["app_state_t"].update(missing="uint32_t"),
    "wrong_enum_value": lambda c: c["ci_app_api"]["enums"]["app_mode_t"].update(APP_MODE_BLINK=2),
    "missing_function": lambda c: c["ci_app_api"]["functions"].update(absent_function=dict(returns="void", arguments=[])),
}


def gdb_env(build):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", TMP=str(build), TEMP=str(build))
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    env.pop("STM32_GDBTEST_STAND", None)
    env.pop("STM32_GDBTEST_IMAGE_POLICY", None)
    return env


def prepare(build, session, test_id, env, expect=0):
    run([sys.executable, "-B", ROOT / "stm32_gdbtest/cli.py", "run", "--session", session, "--test", test_id,
         "--prepare-only"], env=env, expect=expect, log=build / "ci.log")
    reports = sorted((build / "hwtest/runs").glob(f"*-{test_id}-*/result.json"), key=lambda p: p.stat().st_mtime)
    return json.loads(reports[-1].read_text(encoding="utf-8"))


def firmware_pair(gcc, profile):
    toolchain = Path(f"/opt/xpack-arm-none-eabi-gcc-{gcc}")
    build = FIRMWARE / "build" / f"{profile}-gcc{gcc.split('-')[0]}"
    shutil.rmtree(build, ignore_errors=True)
    build.mkdir(parents=True)
    log = build / "ci.log"
    env = gdb_env(build)
    env["ARM_TOOLCHAIN_ROOT"] = str(toolchain)
    run(["cmake", "-S", FIRMWARE, "-B", build, "-G", "Ninja", "--toolchain", FIRMWARE / "cmake/arm-gcc.cmake",
         f"-DCI_PROFILE={profile}", f"-DARM_TOOLCHAIN_ROOT={toolchain}", "-DCMAKE_BUILD_TYPE=Debug",
         "-DSTM32_GDBTEST_STAND="], env=env, log=log)
    run(["cmake", "--build", build], env=env, log=log)

    session_path = build / "hwtest/session.json"
    session = json.loads(session_path.read_text(encoding="utf-8"))
    if Path(session["gdb"]).parent != toolchain / "bin":
        raise CheckError(f"GDB from another toolchain: {session['gdb']}")
    manifest = json.loads((build / "hwtest/build-manifest.json").read_text(encoding="utf-8"))
    sources = {unit["source"] for unit in manifest["units"]}
    inputs = {item["file"] for item in manifest["inputs"]}
    expected_ld = f"profiles/{profile}/firmware_FLASH.ld"
    expected_sources = {"src/startup.c", "src/app.c", "src/board.c"}
    if profile == "f030r8":
        expected_sources.update(("src/adc_f030.c", "src/adc_units.c", "src/rtc_f030.c"))
    if sources != expected_sources:
        raise CheckError(f"Unexpected manifest units: {sorted(sources)}; expected {sorted(expected_sources)}")
    if expected_ld not in inputs:
        raise CheckError(f"Manifest linker input missing: {expected_ld}")
    if manifest["compilers"][0]["version"] != gcc.split("-")[0] or not manifest["cube_packages"]:
        raise CheckError("Manifest compiler version or Cube package differs")
    if any(re.match(r"^(/|[A-Za-z]:)", item["file"]) for item in manifest["inputs"]):
        raise CheckError("Manifest contains absolute paths")
    # Startup copies .data word by word: an unaligned load address faults on Cortex-M0.
    profile_data = tomllib.loads((FIRMWARE / f"profiles/{profile}/target.toml").read_text(encoding="utf-8"))
    sections = run([toolchain / "bin/arm-none-eabi-objdump", "-h", session["elf"]], env=env, log=log)
    regions = parse_sections(sections, profile_data["flash_start"], profile_data["flash_size"])
    unaligned = [r["name"] for r in regions if r["address"] % 4]
    if unaligned or ".data" not in {r["name"] for r in regions}:
        raise CheckError(f"Load sections must include .data and be word-aligned: unaligned {unaligned}")

    # CTest host label: traceability and prepare.<ID> with requested offline contracts.
    ctest = run(["ctest", "--test-dir", build, "-L", "host", "--output-on-failure"], env=env, log=log)
    expected_cases = ["HW_CI_BOOT", "HW_CI_GPIO"]
    if profile == "f030r8":
        expected_cases += ["HW_CI_CLOCK", "HW_CI_BLINK", "HW_CI_TIM3_INIT", "HW_CI_TIM3_IRQ",
                           "HW_CI_ADC_INIT", "HW_CI_ADC_DMA", "HW_CI_ADC_TIMEOUT",
                           "HW_CI_ADC_UNITS", "HW_CI_ADC_VECTORS", "HW_CI_ADC_INVALID",
                           "HW_CI_SLEEP_SYSTICK", "HW_CI_SLEEP_TIM3",
                           "HW_CI_RTC_INIT", "HW_CI_RTC_ALARM", "HW_CI_ADC_BUSY", "HW_CI_RTC_DEADLINE"]
    if profile == "f103c8":
        expected_cases += ["HW_CI_CLOCK", "HW_CI_BLINK", "HW_CI_TIM2_INIT", "HW_CI_TIM2_IRQ", "HW_CI_SYSTICK_IRQ"]
    if any("prepare." + name not in ctest for name in expected_cases):
        raise CheckError("CTest did not run the prepare tests")
    for test_id in expected_cases:
        report = prepare(build, session_path, test_id, env)
        if (report["status"], report["mode"], report["contracts"]["status"]) != ("PASS", "prepare", "PASS"):
            raise CheckError(f"{test_id}: unexpected prepare report")
        if report["connection_attempted"] or report["hardware_accessed"]:
            raise CheckError(f"{test_id}: preparation touched the debugger")

    # Full image policy: canonical BIN and transport ELF are prepared and checked.
    policy = FIRMWARE / f"profiles/{profile}/full-image.toml"
    report = prepare(build, session_path, "HW_CI_GPIO", dict(env, STM32_GDBTEST_IMAGE_POLICY=str(policy)))
    if report["image_verification"]["scope"] != "full-image" or not report.get("program_elf_sha256"):
        raise CheckError("Full-image preparation report is incomplete")
    small = build / "small-image.toml"
    small.write_text(policy.read_text(encoding="utf-8").replace("end = 0x08004000", "end = 0x08000100"),
                     encoding="utf-8")
    report = prepare(build, session_path, "HW_CI_GPIO", dict(env, STM32_GDBTEST_IMAGE_POLICY=str(small)), expect=2)
    if "exceeds full image range" not in report.get("error", ""):
        raise CheckError("Too small image policy was not rejected")

    # An empty loadable section with a RAM LMA must not stretch the BIN (spec 4.1.5, TC-88).
    empty, stretched = build / "empty.bin", build / "empty-ram-section.elf"
    empty.write_bytes(b"")
    run([toolchain / "bin/arm-none-eabi-objcopy", "--add-section", f".ci_empty={empty}",
         "--set-section-flags", ".ci_empty=alloc,load,contents,data",
         "--change-section-address", ".ci_empty=0x20000000", session["elf"], stretched], env=env, log=log)
    if ".ci_empty" not in run([toolchain / "bin/arm-none-eabi-objdump", "-h", stretched], env=env, log=log):
        raise CheckError("objcopy did not add the empty RAM section")
    stretched_session = build / "hwtest/session-empty-ram-section.json"
    variant = {key: value for key, value in session.items() if key != "build_manifest"}
    stretched_session.write_text(json.dumps(dict(variant, elf=str(stretched))), encoding="utf-8")
    report = prepare(build, stretched_session, "HW_CI_BOOT", env)
    bins = sorted((build / "hwtest/runs").glob("*-HW_CI_BOOT-*/image.bin"), key=lambda p: p.stat().st_mtime)
    if report["status"] != "PASS" or bins[-1].stat().st_size > profile_data["flash_size"]:
        raise CheckError(f"Empty RAM section stretched the BIN: {bins[-1].stat().st_size} bytes")

    # Negative ELF contracts: each mutation must stop the offline preflight with ERROR.
    registry = FIRMWARE / f"profiles/{profile}/tests/contracts.json"
    base = select_contracts(registry, ["ci_gpio_macros", "ci_app_api"], manifest)
    negatives = build / "negative"
    negatives.mkdir()
    for name, mutate in NEGATIVE_CONTRACTS.items():
        selected = copy.deepcopy(base)
        mutate(selected["contracts"])
        request, result = negatives / f"{name}.request.json", negatives / f"{name}.result.json"
        request.write_text(json.dumps(dict(elf=session["elf"], result=str(result), selected=selected)),
                           encoding="utf-8")
        run([session["gdb"], "-nx", "-batch", "-q", "-iex", "set auto-load off", session["elf"],
             "-x", ROOT / "stm32_gdbtest/contract_preflight.py"],
            env=dict(env, STM32_GDBTEST_CONTRACT_REQUEST=str(request)), expect=2, log=log)
        evidence = json.loads(result.read_text(encoding="utf-8"))
        if evidence["status"] != "ERROR" or evidence["connection_attempted"]:
            raise CheckError(f"Negative contract {name} was not rejected")
    return f"{len(NEGATIVE_CONTRACTS)} negative contracts rejected"


def level_firmware(record, gccs, profiles):
    for gcc in gccs:
        for profile in profiles:
            record(f"firmware.{profile}.gcc-{gcc}", lambda g=gcc, p=profile: firmware_pair(g, p))


# --- main -----------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("levels", nargs="*", metavar="{docs,format,host,firmware,hal}")
    parser.add_argument("--gcc", action="append", choices=LOCK["gcc_versions"])
    parser.add_argument("--profile", action="append", choices=LOCK["profiles"])
    args = parser.parse_args()
    unknown = sorted(set(args.levels) - {"docs", "format", "host", "firmware", "hal"})
    if unknown:
        parser.error(f"unknown level: {', '.join(unknown)}")
    levels = args.levels or ["docs", "format", "host", "firmware", "hal"]
    OUT.mkdir(parents=True, exist_ok=True)
    results = []

    def record(name, check):
        started = time.monotonic()
        try:
            detail = check()
            status = "PASS"
        except Exception as error:  # every failure is reported, the run continues
            status, detail = "FAIL", str(error)
        # Failures keep the full message; successful checks keep only a short note.
        note = detail if isinstance(detail, str) and (status == "FAIL" or len(detail) < 200) else None
        results.append(dict(name=name, status=status, seconds=round(time.monotonic() - started, 1), detail=note))
        print(f"{status} {name} ({results[-1]['seconds']}s)" + (f"\n{detail}" if status == "FAIL" else ""),
              flush=True)

    if "docs" in levels:
        level_docs(record)
    if "format" in levels:
        level_format(record)
    if "host" in levels:
        level_host(record)
    if "firmware" in levels:
        level_firmware(record, args.gcc or LOCK["gcc_versions"], args.profile or LOCK["profiles"])
    if "hal" in levels:
        from ci.hal_f030 import check
        record("hal.f030.gcc13", lambda: check(run))
    summary = dict(schema=1, levels=levels, cmake=os.environ.get("CMAKE_VERSION"),
                   passed=sum(r["status"] == "PASS" for r in results), total=len(results), results=results)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{summary['passed']}/{summary['total']} checks passed; {OUT / 'summary.json'}")
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
