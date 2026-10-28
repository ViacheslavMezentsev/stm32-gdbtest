"""A6: офлайн-импорт ROS1 bag v2, отдельный анализ и негативные копии.

Без аргументов — синтетическая кампания (CI). С --bag — локальный импорт реальной
записи по локальному контракту; исходные файлы только читаются.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
import analysis  # noqa: E402
import fixture  # noqa: E402
import importer  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CHANNELS = {"/demo/sys/uptime_s": {"name": "uptime", "unit": "s"},
            "/demo/sensor/level_v": {"name": "level", "unit": "V"},
            "/demo/sensor/reference_v": {"name": "reference", "unit": "V"},
            "/demo/state/mode": {"name": "mode", "unit": None},
            "/demo/state/ready": {"name": "ready", "unit": None}}
MANIFEST = {"schema": 1, "scope": "synthetic_bag", "record_window_ms": 1000, "gap_ms": 1000,
            "anchor": {"channel": "uptime", "unit": "s", "scale_ms": 1000, "gdb_field": "tick"},
            "clock": {"max_latency_ms": 20, "basis": "fixture"}, "gdb_record": "debug_values",
            "compare": [{"gdb": "level", "channel": "level", "kind": "float32", "unit": "V", "tolerance": 1e-4},
                        {"gdb": "reference", "channel": "reference", "kind": "float32", "unit": "V",
                         "tolerance": 1e-4}]}
# Вариант → (bag, ожидаемый вердикт анализа, причина). Ожидания заданы до запуска.
CASES = {"normal": ("normal", "PASS", "correlated"), "bz2": ("bz2", "PASS", "correlated"),
         "mismatch": ("normal", "FAIL", "value_mismatch"), "boundary": ("normal", "UNKNOWN", "time_boundary"),
         "truncated": ("truncated", "UNKNOWN", "import_invalid"),
         "unindexed": ("unindexed", "UNKNOWN", "import_invalid"),
         "index_mismatch": ("index_mismatch", "UNKNOWN", "import_invalid"),
         "lz4": ("lz4", "UNKNOWN", "import_invalid"), "wrong_type": ("wrong_type", "UNKNOWN", "channel_contract"),
         "bad_md5": ("bad_md5", "UNKNOWN", "channel_contract"),
         "wrong_channel": ("wrong_channel", "UNKNOWN", "channel_contract"),
         "wrong_unit": ("normal", "UNKNOWN", "channel_contract"), "nan": ("nan", "UNKNOWN", "nonfinite_value"),
         "wrong_identity": ("normal", "UNKNOWN", "identity"), "metadata_mismatch": ("normal", "UNKNOWN", "identity"),
         "clock_shift": ("clock_shift", "UNKNOWN", "clock_shift"),
         "no_anchor": ("no_anchor", "UNKNOWN", "clock_unqualified"),
         "assumed_clock": ("normal", "UNKNOWN", "clock_assumed"),
         "halted": ("halted", "UNKNOWN", "moment_outside_anchors"),
         "reset": ("reset", "UNKNOWN", "moment_ambiguous"),
         "snapshot_missing": ("normal", "UNKNOWN", "snapshot_missing"),
         "scenario_fail": ("normal", "UNKNOWN", "scenario_not_pass"), "repeat": ("normal", "PASS", "correlated")}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def finish(folder, blob, channels, manifest, capture, scenario, records):
    """Импорт, сохранение, анализ по файлам и перечень SHA-256."""
    (folder / "source.bag").write_bytes(blob)
    imported, lines = importer.import_bag(blob, channels)
    save(folder / "manifest.json", manifest)
    save(folder / "import.json", imported)
    (folder / "samples.jsonl").write_text("".join(line + "\n" for line in lines), encoding="utf-8")
    save(folder / "capture.json", capture)
    save(folder / "scenario.json", scenario)
    save(folder / "records.json", records)
    names = analysis.FILES + ("source.bag",)
    save(folder / "sha256.json", {name: hashlib.sha256((folder / name).read_bytes()).hexdigest() for name in names})
    outcome = analysis.analyze_files(folder)
    save(folder / "analysis.json", outcome)
    return imported, outcome


def synthetic(folder, case):
    variant, verdict, reason = CASES[case]
    folder.mkdir()
    blob, summary = fixture.build(variant)
    channels, manifest = copy.deepcopy(CHANNELS), copy.deepcopy(MANIFEST)
    capture = fixture.capture(blob, summary, "wrong_identity" if case == "wrong_identity" else variant)
    if case == "metadata_mismatch":
        capture["bag"]["messages"] += 1
    if case == "wrong_unit":
        channels["/demo/sensor/level_v"]["unit"] = "mV"
    if case == "assumed_clock":
        manifest["clock"]["basis"] = "assumed"
    run_id = f"demo-{case}"
    # Снимок отладчика задан моделью: тик МК в мс и значения переменных в момент чтения.
    tick = {"boundary": 6200, "halted": 5600, "reset": 4200}.get(case, 5200)
    snapshot = {"level": 3.75 if case == "mismatch" else 2.5, "reference": 1.0, "tick": tick}
    records = {"schema": 1, "run_id": run_id, "case_id": "DEMO_TELEMETRY",
               "records": [{"sequence": 1, "name": "debug_values", "data": snapshot}]}
    if case == "snapshot_missing":
        records["records"] = []
    scenario = {"status": "FAIL" if case == "scenario_fail" else "PASS", "case_id": "DEMO_TELEMETRY",
                "run_id": run_id, "mode": "model"}
    imported, outcome = finish(folder, blob, channels, manifest, capture, scenario, records)
    again = analysis.analyze_files(folder)
    ok = (outcome["verdict"], outcome["reason"]) == (verdict, reason) and again == outcome
    return {"case": case, "import": imported["status"], "import_reason": imported.get("reason"),
            "analysis": outcome["verdict"], "reason": outcome["reason"], "ok": ok}


def utc_ns(text):
    stamp = datetime.strptime(text, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    return int(stamp.timestamp()) * 1_000_000_000 + stamp.microsecond * 1000


def local(folder, args):
    """Реальная запись: исходные файлы читаются, в каталог кампании пишутся только копии и производные."""
    folder.mkdir()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    meta = json.loads(args.capture.read_text(encoding="utf-8"))
    result = json.loads(args.result.read_text(encoding="utf-8"))
    records = json.loads(args.records.read_text(encoding="utf-8"))
    blob = args.bag.read_bytes()
    bag = meta["bag"]
    # Из метаданных переносятся только нужные поля: без порта, серийных номеров и путей.
    capture = {"schema": 1, "test": meta["test"], "status": meta["status"],
               "record_start_ns": utc_ns(meta["record_start_utc"]), "record_stop_ns": utc_ns(meta["record_stop_utc"]),
               "bag": {"messages": bag["messages"], "size": bag["size"], "start_ns": round(bag["start"] * 1e9),
                       "end_ns": round(bag["end"] * 1e9), "topics": sorted(t["topic"] for t in bag["topics"])}}
    scenario = {"status": result["status"], "case_id": result["id"], "run_id": result["run_id"],
                "mode": result["mode"], "elf_sha256": result.get("elf_sha256")}
    imported, outcome = finish(folder, blob, contract["channels"], contract["manifest"], capture, scenario, records)
    expected = contract.get("expected")
    ok = expected is None or [outcome["verdict"], outcome["reason"]] == expected
    return {"case": "local", "import": imported["status"], "import_reason": imported.get("reason"),
            "messages": imported.get("bag", {}).get("messages"), "channels": len(imported["channels"]),
            "analysis": outcome["verdict"], "reason": outcome["reason"], "ok": ok}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--bag", type=Path)
    parser.add_argument("--capture", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--records", type=Path)
    parser.add_argument("--contract", type=Path)
    args = parser.parse_args()
    real = [args.bag, args.capture, args.result, args.records, args.contract]
    if any(real) and not all(real):
        parser.error("--bag, --capture, --result, --records и --contract задаются вместе")
    out = args.output or ROOT / "build/rosbag-import" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True, exist_ok=False)
    inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(__file__).parent.glob("*.py"))}
    results = []
    summary = {"status": "ERROR", "inputs": inputs, "results": results}
    try:
        if all(real):
            results.append(local(out / "local", args))
        else:
            for case in CASES:
                results.append(synthetic(out / case, case))
        for row in results:
            print(row["case"], row["import"], row["analysis"], row["reason"], "OK" if row["ok"] else "MISMATCH")
        summary["status"] = "PASS" if results and all(r["ok"] for r in results) else "ERROR"
    finally:
        save(out / "summary.json", summary)
        print(out / "summary.json")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
