"""Отдельный анализ импортированной записи и снимка отладчика.

Исход сценария и сохранённые файлы не переписываются. Порядок: импорт →
сценарий → идентичность → окно часов → контракт каналов → конечность →
опоры времени → момент чтения GDB → значения. Любое непроверяемое звено даёт
UNKNOWN; FAIL только при полной временной определённости и явном расхождении.
ROS и GDB читают одно и то же состояние прошивки: согласие двух транспортов не
является независимым измерением.
"""
import hashlib
import json
import math
from pathlib import Path

FILES = ("manifest.json", "import.json", "samples.jsonl", "capture.json", "scenario.json", "records.json")
LIMIT = 16 * 1024 * 1024
BASES = {"synthetic_bag": ("fixture",), "local_recording": ("measured",)}


def analyze(manifest, imported, samples, capture, scenario, records):
    scope = manifest.get("scope")
    result = {"verdict": "UNKNOWN", "reason": None, "scope": scope, "scenario_status": scenario.get("status"),
              "independence": "same_firmware_state"}

    def answer(verdict, reason, **extra):
        result.update(extra, verdict=verdict, reason=reason)
        return result

    if imported.get("status") != "COMPLETE":
        return answer("UNKNOWN", "import_invalid", detail=imported.get("reason"))
    if scenario.get("status") != "PASS":
        return answer("UNKNOWN", "scenario_not_pass")
    bag = imported["bag"]
    topics = sorted(c["topic"] for c in imported["channels"])
    meta = capture.get("bag", {})
    # Идентичность: один опыт в метаданных захвата, сценарии и записях; сводка bag совпадает.
    if not (capture.get("test") == scenario.get("case_id") == records.get("case_id")
            and scenario.get("run_id") == records.get("run_id")
            and meta.get("messages") == bag["messages"] and meta.get("size") == imported["source"]["bytes"]
            and meta.get("topics") == topics and meta.get("start_ns") is not None
            and abs(meta["start_ns"] - bag["start_ns"]) <= 2000 and abs(meta["end_ns"] - bag["end_ns"]) <= 2000):
        return answer("UNKNOWN", "identity")
    window = manifest["record_window_ms"] * 1_000_000
    if not (capture["record_start_ns"] - window <= bag["start_ns"] <= bag["end_ns"]
            <= capture["record_stop_ns"] + window):
        return answer("UNKNOWN", "clock_shift")
    channels = {c["name"]: c for c in imported["channels"]}
    anchor = manifest["anchor"]
    # Контракт сравниваемых каналов: наличие, расшифровка, тип и единицы.
    for item in manifest["compare"]:
        channel = channels.get(item["channel"])
        if (channel is None or not channel["decoded"] or channel["kind"] != item["kind"]
                or channel["unit"] != item["unit"]):
            return answer("UNKNOWN", "channel_contract", channel=item["channel"])
    if any(channels[item["channel"]]["nonfinite"] for item in manifest["compare"]):
        return answer("UNKNOWN", "nonfinite_value")
    series = {}
    for row in samples:
        series.setdefault(row["channel"], []).append(row)
    gaps = gaps_of(samples, manifest["gap_ms"] * 1_000_000)
    result["gaps"] = gaps
    clock = channels.get(anchor["channel"])
    if (clock is None or not clock["decoded"] or clock["kind"] not in ("uint32", "int32")
            or clock["unit"] != anchor["unit"]):
        return answer("UNKNOWN", "clock_unqualified")
    segments = anchors(series.get(anchor["channel"], []))
    result["segments"] = [{"first": s["first"], "last": s["last"], "anchors": len(s["anchors"])} for s in segments]
    snapshot = next((r["data"] for r in records.get("records", []) if r.get("name") == manifest["gdb_record"]), None)
    tick = snapshot.get(anchor["gdb_field"]) if isinstance(snapshot, dict) else None
    if type(tick) is not int or tick < 0:
        return answer("UNKNOWN", "snapshot_missing")
    whole, scale = tick // anchor["scale_ms"], anchor["scale_ms"]
    candidates = [s for s in segments if whole in s["anchors"] and whole + 1 in s["anchors"]]
    location = {"tick_ms": tick, "anchor_s": whole, "candidates": len(candidates)}
    if not candidates:
        nearest = [s for s in segments if s["first"] <= whole <= s["last"] + 1]
        if nearest:
            location["last_anchor_s"] = nearest[0]["last"]
        return answer("UNKNOWN", "moment_outside_anchors", location=location)
    if len(candidates) > 1:
        return answer("UNKNOWN", "moment_ambiguous", location=location)
    latency = manifest["clock"].get("max_latency_ms")
    basis = manifest["clock"].get("basis")
    if type(latency) not in (int, float) or not math.isfinite(latency) or latency < 0:
        return answer("UNKNOWN", "clock_unqualified", location=location)
    if basis not in BASES.get(scope, ()):
        return answer("UNKNOWN", "clock_assumed", location=location)
    lat = int(latency * 1_000_000)
    # Возможный момент чтения: от последнего приёма k-1 минус задержка до первого приёма k+1.
    low, high = candidates[0]["anchors"][whole][0] - lat, candidates[0]["anchors"][whole + 1][1]
    location.update(low_ns=low, high_ns=high, fraction=(tick % scale) / scale)
    result["location"] = location
    verdicts = {}
    for item in manifest["compare"]:
        expected = snapshot.get(item["gdb"])
        if type(expected) not in (int, float) or not math.isfinite(expected):
            return answer("UNKNOWN", "snapshot_missing", location=location)
        values = [r["value"] for r in series.get(item["channel"], []) if low <= r["t_ns"] <= high + lat]
        if not values:
            verdicts[item["channel"]] = "no_sample"
            continue
        close = [abs(v - expected) <= item["tolerance"] for v in values]
        verdicts[item["channel"]] = "match" if all(close) else "mismatch" if not any(close) else "boundary"
    result["channels"] = verdicts
    if "mismatch" in verdicts.values():
        return answer("FAIL", "value_mismatch")
    if any(v != "match" for v in verdicts.values()):
        return answer("UNKNOWN", "time_boundary")
    return answer("PASS", "correlated")


def anchors(rows):
    """Сегменты счётчика uptime: убывание — новый сегмент; переход k-1→k даёт (последний k-1, первый k)."""
    segments, previous = [], None
    for row in rows:
        value = row["value"]
        if previous is None or value < previous["value"]:
            segments.append({"first": value, "last": value, "anchors": {}})
        elif value == previous["value"] + 1:
            segments[-1]["anchors"][value] = (previous["t_ns"], row["t_ns"])
        segments[-1]["last"] = value
        previous = row
    return segments


def gaps_of(samples, threshold):
    times = sorted(r["t_ns"] for r in samples)
    return [{"after_ns": a, "duration_ms": (b - a) // 1_000_000} for a, b in zip(times, times[1:]) if b - a > threshold]


def analyze_files(folder):
    folder = Path(folder)

    def raw(name):
        data = (folder / name).read_bytes()
        if len(data) > LIMIT:
            raise ValueError(f"{name} too large")
        return data

    try:
        if (folder / "sha256.json").exists():
            hashes = json.loads(raw("sha256.json"))
            for name in FILES + ("source.bag",):
                if (folder / name).exists() and hashlib.sha256(raw(name)).hexdigest() != hashes.get(name):
                    raise ValueError(f"artifact hash mismatch: {name}")
        manifest, imported, _, capture, scenario, records = (
            json.loads(raw(name)) if name != "samples.jsonl" else None for name in FILES)
        samples = [json.loads(line) for line in raw("samples.jsonl").splitlines()]
        return analyze(manifest, imported, samples, capture, scenario, records)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return {"verdict": "UNKNOWN", "reason": "artifact_invalid", "detail": str(error)}


if __name__ == "__main__":
    import sys
    outcome = analyze_files(sys.argv[1])
    print(json.dumps(outcome, ensure_ascii=False, indent=2))
    raise SystemExit(0 if outcome["verdict"] == "PASS" else 1 if outcome["verdict"] == "FAIL" else 2)
