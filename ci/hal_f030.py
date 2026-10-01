"""TC-130: real F030 HAL ELF, exact inventory and negative contracts, no server."""
import copy
import json
import os
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from stm32_gdbtest.collect import collect
from stm32_gdbtest.contracts import select_contracts

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/hal-f030"
EXPECTED = {"HW_BOOT", "HW_CLOCK", "HW_GPIO", "HW_BLINK", "HW_ADC_DMA_INIT",
            "HW_TIM3_INIT", "HW_RTC_INIT", "HW_ADC_DMA_RUNTIME", "HW_TIM3_IRQ",
            "HW_RTC_ALARM", "HW_ADC_START_ERROR", "HW_ADC_DMA_TIMEOUT",
            "HW_ADC_UNITS", "HW_ADC_INVALID", "HW_ADC_VECTORS",
            "HW_SLEEP_SYSTICK", "HW_SLEEP_TIMER", "HW_GPIO_ARGUMENTS",
            "HW_GPIO_FILTERED_CALL", "HW_RCC_ERROR", "HW_RCC_OSC_NULL", "HW_RCC_CLOCK_NULL"}


def check(run):
    build = FIXTURE / "build/ci-gcc13"
    build.mkdir(parents=True, exist_ok=True)
    log = build / "ci.log"
    log.write_text("", encoding="utf-8")
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(("STM32_GDBTEST_", "HWTEST_")) and k not in ("PYTHONPATH", "PYTHONHOME")}
    env.update(PYTHONDONTWRITEBYTECODE="1", TMP=str(build), TEMP=str(build), TMPDIR=str(build))
    toolchain = Path(env.get("ARM_TOOLCHAIN_ROOT", str(
        Path.home() / "xpack-arm-none-eabi-gcc-13.3.1-1.1" if os.name == "nt"
        else Path("/opt/xpack-arm-none-eabi-gcc-13.3.1-1.1")))).resolve()
    run(["cmake", "-S", FIXTURE, "-B", build, "-G", "Ninja", "--toolchain",
         FIXTURE / "cmake/arm-gcc.cmake", f"-DARM_TOOLCHAIN_ROOT={toolchain}",
         "-DCMAKE_BUILD_TYPE=Debug", "-DSTM32_GDBTEST_STAND="], env=env, log=log)
    run(["cmake", "--build", build], env=env, log=log)
    session = json.loads((build / "hwtest/session.json").read_text(encoding="utf-8"))
    if session["stand"] or Path(session["gdb"]).resolve().parent != toolchain / "bin":
        raise ValueError("HAL session must be offline and use the selected toolchain GDB")
    manifest = json.loads(Path(session["build_manifest"]).read_text(encoding="utf-8"))
    if {c["version"] for c in manifest["compilers"]} != {"13.3.1"}:
        raise ValueError("HAL CI baseline requires GCC13.3.1")
    for unit in manifest["units"]:
        if not {"-Og", "-g3", "-fno-lto"}.issubset(unit["flags"]):
            raise ValueError("HAL unit missing debug/no-LTO flags: " + unit["source"])
    if any(re.match(r"^(/|[A-Za-z]:)", item["file"]) for item in manifest["inputs"]):
        raise ValueError("Absolute input path in HAL manifest")
    cases = collect(FIXTURE / "profile/tests/board")
    if len(cases) != 22 or {c["id"] for c in cases} != EXPECTED:
        raise ValueError("HAL case inventory differs")
    inventory = json.loads(run(["ctest", "--test-dir", build, "-L", "host", "--show-only=json-v1"],
                               env=env, log=log))["tests"]
    names = {"prepare." + name for name in EXPECTED} | {"host.traceability", "host.fixture"}
    if len(inventory) != 24 or {t["name"] for t in inventory} != names:
        raise ValueError("HAL CTest inventory differs")
    for test in inventory:
        if test["name"].startswith("prepare.") and "--prepare-only" not in test["command"]:
            raise ValueError("HAL prepare command may access hardware")
    before = set((build / "hwtest/runs").glob("*/result.json"))
    junit = build / "junit.xml"
    junit.unlink(missing_ok=True)
    run(["ctest", "--test-dir", build, "-L", "host", "--output-on-failure", "--no-tests=error",
         "--output-junit", junit], env=env, log=log)
    results = ET.parse(junit).getroot().findall(".//testcase")
    if len(results) != 24 or {r.attrib["name"] for r in results} != names or any(
            r.find(tag) is not None for r in results for tag in ("skipped", "failure", "error")):
        raise ValueError("Incomplete HAL JUnit")
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in
               set((build / "hwtest/runs").glob("*/result.json")) - before]
    if len(reports) != 22 or {r["id"] for r in reports} != EXPECTED:
        raise ValueError("Expected exactly 22 fresh HAL prepare reports")
    requested = {c["id"]: bool(c.get("contracts")) for c in cases}
    for r in reports:
        if (r["status"] != "PASS" or r["mode"] != "prepare" or r["connection_attempted"]
                or r["hardware_accessed"] or r["elf_sha256"] != manifest["elf_sha256"]):
            raise ValueError("Invalid HAL prepare evidence")
        if requested[r["id"]] and r["contracts"]["status"] != "PASS":
            raise ValueError("Requested HAL contracts were not checked")
    selected = select_contracts(build / "profile/tests/contracts.json",
                                ["gpio_macros", "adc_start_error", "adc_dma_timeout"], manifest)
    def missing_macro(c):
        c["gpio_macros"]["macros"]["expressions"].append("HAL_CI_MISSING_MACRO")
    def bad_context(c):
        c["gpio_macros"]["macros"]["context"] = "hal_ci_missing_context"
    def bad_return(c):
        c["adc_start_error"]["functions"]["HAL_ADC_Start_DMA"]["returns"] = "uint8_t"
    def bad_enum(c):
        c["adc_start_error"]["enums"]["HAL_StatusTypeDef"]["HAL_ERROR"] = 99
    def bad_callback(c):
        c["adc_dma_timeout"]["functions"]["HAL_ADC_ConvCpltCallback"]["arguments"][0]["type"] = "uint32_t"
    variants = [("positive", None, None), ("missing_macro", missing_macro, "gpio_macros"),
                ("wrong_context", bad_context, "gpio_macros"),
                ("wrong_return", bad_return, "adc_start_error"),
                ("wrong_enum", bad_enum, "adc_start_error"),
                ("wrong_callback", bad_callback, "adc_dma_timeout")]
    out = build / "contracts"
    out.mkdir(exist_ok=True)
    for name, mutate, failed_contract in variants:
        contract = copy.deepcopy(selected)
        if mutate:
            mutate(contract["contracts"])
        request, result = out / f"{name}.request.json", out / f"{name}.result.json"
        result.unlink(missing_ok=True)
        request.write_text(json.dumps(dict(elf=session["elf"], result=str(result), selected=contract)), encoding="utf-8")
        run([session["gdb"], "-nx", "-batch", "-q", "-iex", "set auto-load off", session["elf"],
             "-x", ROOT / "stm32_gdbtest/contract_preflight.py"],
            env=dict(env, STM32_GDBTEST_CONTRACT_REQUEST=str(request)),
            expect=2 if mutate else 0, timeout=45, log=log)
        evidence = json.loads(result.read_text(encoding="utf-8"))
        if (evidence["status"] != ("ERROR" if mutate else "PASS") or evidence["connection_attempted"]
                or evidence["elf_sha256"] != manifest["elf_sha256"]):
            raise ValueError("Incorrect HAL contract verdict: " + name)
        if mutate and failed_contract not in {e["contract"] for e in evidence.get("errors", [])}:
            raise ValueError("Negative failed for an unrelated reason: " + name)
    return "24 CTest, 22 fresh prepare reports, positive + 5 rejected HAL contracts"
