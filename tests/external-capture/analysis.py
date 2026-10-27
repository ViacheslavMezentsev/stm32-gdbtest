"""Отдельный вердикт: исход сценария никогда не переписывается."""
import math
import json
import hashlib
from pathlib import Path


def analyze(manifest, scenario, capture, rows):
    def answer(verdict, reason):
        return {"verdict": verdict, "reason": reason, "scenario_status": scenario.get("status"),
                "scope": "synthetic_host_joint_capture"}

    def unknown(reason):
        return answer("UNKNOWN", reason)

    if capture.get("status") != "COMPLETE" or capture.get("cleanup") != "VERIFIED":
        return unknown("capture_incomplete")
    if scenario.get("status") != "PASS":
        return unknown("scenario_not_pass")
    if scenario.get("run") != manifest["run"] or scenario.get("revision") != manifest["revision"]:
        return unknown("scenario_identity")
    if not (type(capture.get("ready_ns")) is int and type(capture.get("window_start_ns")) is int
            and type(capture.get("closed_ns")) is int
            and capture["ready_ns"] <= capture["window_start_ns"] <= capture["closed_ns"]):
        return unknown("readiness_order")
    if manifest.get("expected_count") != 3 or manifest.get("tolerance_ticks") != 2:
        return unknown("unsupported_contract")
    if not rows or rows[-1].get("kind") != "end":
        return unknown("end_marker")
    if len(rows) != 5 or rows[0] != {"kind": "ready", "source": "fixture"}:
        return unknown("inventory")
    samples, end = rows[1:-1], rows[-1]
    if end != {"kind": "end", "run": manifest["run"], "count": 3}:
        return unknown("end_marker")
    if [r.get("seq") for r in samples] != [0, 1, 2]:
        return unknown("sequence")
    for row in samples:
        if any(row.get(key) != value for key, value in
               {"kind": "sample", "source": "fixture", "run": manifest["run"],
                "revision": manifest["revision"], "channel": "signal", "unit": "unit"}.items()):
            return unknown("sample_identity")
        if any(type(row.get(key)) is not int for key in ("seq", "source_tick", "value")):
            return unknown("sample_type")
    clock = manifest["clock"]
    anchors = clock.get("anchors", [])
    if len(anchors) != 2 or clock.get("kind") != "fixture_offset":
        return unknown("clock_unqualified")
    if anchors != [[0, 1000], [40, 1040]]:
        return unknown("clock_unqualified")
    uncertainty = clock.get("uncertainty")
    if type(uncertainty) not in (int, float) or not math.isfinite(uncertainty) or not 0 <= uncertainty <= 2:
        return unknown("clock_uncertainty")
    expected = [(10, 10), (20, 20), (30, 30)]
    if scenario.get("samples") != [{"tick": tick, "value": value} for tick, value in expected]:
        return unknown("scenario_samples")
    # Полный интервал неопределённости должен помещаться в допуск ±2 тика.
    offsets = [row["source_tick"] - 1000 - tick for row, (tick, _) in zip(samples, expected)]
    if any(abs(offset) - uncertainty > 2 for offset in offsets):
        return answer("FAIL", "time_outside_tolerance")
    if any(abs(offset) + uncertainty > 2 for offset in offsets):
        return unknown("time_boundary")
    if [row["value"] for row in samples] != [10, 20, 30]:
        return answer("FAIL", "value_mismatch")
    return answer("PASS", "correlated")


def analyze_files(folder):
    folder = Path(folder)
    def load(name):
        data = (folder / name).read_bytes()
        if len(data) > 65536:
            raise ValueError("fixture artifact too large")
        return json.loads(data)
    try:
        manifest, scenario, capture = (load(name) for name in ("manifest.json", "scenario.json", "capture.json"))
        if (folder / "sha256.json").exists():
            hashes = load("sha256.json")
            for name in ("manifest.json", "scenario.json", "capture.json", "external.jsonl"):
                if hashlib.sha256((folder / name).read_bytes()).hexdigest() != hashes.get(name):
                    raise ValueError("artifact hash mismatch")
        raw = (folder / "external.jsonl").read_bytes()
        if len(raw) > 65536:
            raise ValueError("fixture capture too large")
        rows = [json.loads(line) for line in raw.splitlines()]
        return analyze(manifest, scenario, capture, rows)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return {"verdict": "UNKNOWN", "reason": "artifact_invalid", "detail": str(error),
                "scope": "synthetic_host_joint_capture"}


if __name__ == "__main__":
    import sys
    result = analyze_files(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["verdict"] == "PASS" else 1 if result["verdict"] == "FAIL" else 2)
