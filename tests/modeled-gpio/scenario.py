"""RU: Диагностический GDB probe: потребление GPIO и границы override.
EN: Diagnostic GDB probe: GPIO consumption and override boundaries.
"""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import sys
import gdb


# Пути принадлежат локальной обвязке, платы не используются.
ROOT = Path(os.environ["GPIO_ROOT"])
sys.path[:0] = [str(ROOT), str(ROOT / "tests/modeled-gpio")]
from analysis import assess, LEVELS
from stm32_gdbtest.configuration import load_session
from stm32_gdbtest.target import Target
from stm32_gdbtest.result_capture import save, finalize, read


# Target получает снимок SVD и штатный журнал.
config = load_session(ROOT / "tests/modeled-gpio/session.toml")
t = Target({"checks": []}, dict(config.config["target"]), config)
output = Path(os.environ["DDTT_PROBE_RESULT"])
stimulus = Path(os.environ["GPIO_STIMULUS"])
log = Path(os.environ["GPIO_LOG"])
data = {"scope": "modeled-gpio-not-electrical", "consumption": [], "cpu_callbacks": []}
generation = 1
saved = None


# Внешний источник меняется только при остановленном ядре; следующий доступ применит уровень.
def drive(pins):
    global generation
    generation += 1
    temporary = stimulus.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(generation=generation, pins=pins)), encoding="utf-8")
    temporary.replace(stimulus)
    t.record("model.input", {"pins": pins, "generation": generation})


# Навигация синхронна: это probe вне async-сценария, все вызовы в главном потоке GDB.
def reach(symbol):
    gdb.Breakpoint(symbol, temporary=True, internal=True)
    gdb.execute("continue")


# Независимый журнал модели считает реальные callbacks, а не записи намерений API.
def events():
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []


# Отказ проверяем до передачи серверу, включая вариант с одним reason.
def refused(action):
    start = len(events())
    try:
        action()
    except Exception as error:
        return {"code": getattr(error, "code", None), "callbacks": len(events()) - start}
    return {"code": None, "callbacks": len(events()) - start}


# Возвращаем весь POD и внешний источник, затем проверяем оба независимых ресурса.
def restore():
    t.memory(address, saved)
    drive(2)
    return {"memory": t.memory(address, len(saved)) == saved, "input": t.mmio.read("GPIO.IDR") == 2}


try:
    reach("ready")
    symbol = t.symbol("observation")
    address = symbol["address"]
    saved = t.memory(address, symbol["size"])
    data["snapshot"] = {"bytes": len(saved), "sha256": hashlib.sha256(saved).hexdigest()}
    data["refusal"] = refused(lambda: t.mmio.write("GPIO.IDR", 3))
    data["reason_refusal"] = refused(lambda: t.mmio.write("GPIO.IDR", 3, reason="not permission"))
    override = replace(config.svd_catalog.registers["GPIO.IDR"], access="read-write")
    missing = refused(lambda: t.mmio.write("GPIO.IDR", 3, override=override))
    data["missing_reason"] = {"callbacks": missing["callbacks"], "refused": missing["code"] is not None}
    start = len(events())
    data["ack"] = t.mmio.write("GPIO.IDR", 3, override=override,
                               reason="negative control: model ignores writes to input")
    data["override_callbacks"] = events()[start:]
    data["readback"] = t.mmio.read("GPIO.IDR")
    attempts = t.records("mmio.attempt")
    data["override_audit"] = any(row["data"].get("override") is True
                                 and row["data"].get("reason") == "negative control: model ignores writes to input"
                                 for row in attempts)

    # Первый проход без drive показывает отсутствие эффекта override; далее меняется внешний вход.
    for index, pins in enumerate(LEVELS):
        if index:
            reach("ready")
            drive(pins)
        start = len(events())
        reach("sampled")
        data["cpu_callbacks"].append(events()[start:])
        row = {name: t.read("observation." + name) for name in ("raw", "active", "neighbour", "samples")}
        data["consumption"].append(row)
        t.record("gpio.consumed", row)
    data["negative_control"] = {"status": "FAIL" if data["consumption"][0]["active"] != 1 else "PASS",
                                "claim": "override forces input high", "expected": 1,
                                "actual": data["consumption"][0]["active"]}
    data["restoration"] = restore()

    # Исключение до resume: изменения SRAM и внешнего источника также должны быть отменены.
    try:
        drive(3)
        t.write("observation.active", 9)
        raise RuntimeError("intentional interruption before resume")
    except RuntimeError as error:
        data["interruption"] = str(error)
    finally:
        data["exception_restoration"] = restore()
finally:
    try:
        if saved is not None:
            data["final_restoration"] = restore()
        checks = assess(data)
        checks.append({"name": "final restoration", "passed": data.get("final_restoration") == {
            "memory": True, "input": True}})
        t.record("gpio.analysis", {"checks": checks})
        capture = output.parent / "capture"
        capture.mkdir()
        report = {"id": "GPIO_MODEL", "run_id": output.parent.name,
                  "status": "PASS" if all(c["passed"] for c in checks) else "FAIL"}
        save(capture, report, t, "normal")
        finalize(capture, report, True)
        read(capture, report)
        (capture / "result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        output.with_name("observations.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
        output.with_name("negative-control.json").write_text(json.dumps(data.get("negative_control")), encoding="utf-8")
        output.write_text(json.dumps({"status": report["status"], "checks": checks}, indent=2), encoding="utf-8")
    finally:
        t.close()
