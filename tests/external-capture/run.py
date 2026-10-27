"""TECH-026: host-модель сценария и отдельный процесс внешнего захвата."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import uuid

from analysis import analyze_files

ROOT = Path(__file__).resolve().parents[2]
CASES = {"normal": ("PASS", "correlated"), "drop": ("UNKNOWN", "inventory"),
         "duplicate": ("UNKNOWN", "inventory"), "reorder": ("UNKNOWN", "sequence"),
         "wrong_run": ("UNKNOWN", "sample_identity"), "wrong_revision": ("UNKNOWN", "sample_identity"),
         "wrong_unit": ("UNKNOWN", "sample_identity"), "wrong_channel": ("UNKNOWN", "sample_identity"),
         "truncated": ("UNKNOWN", "artifact_invalid"), "no_end": ("UNKNOWN", "end_marker"),
         "not_ready": ("UNKNOWN", "capture_incomplete"), "timeout": ("UNKNOWN", "capture_incomplete"),
         "bad_clock": ("UNKNOWN", "clock_unqualified"), "uncertain_clock": ("UNKNOWN", "clock_uncertainty"),
         "time_boundary": ("UNKNOWN", "time_boundary"), "time_violation": ("FAIL", "time_outside_tolerance"),
         "mismatch": ("FAIL", "value_mismatch"), "scenario_fail": ("UNKNOWN", "scenario_not_pass"), "repeat": ("PASS", "correlated")}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def capture_one(folder, mode, revision):
    folder.mkdir()
    run_id = uuid.uuid4().hex
    manifest = {"run": run_id, "revision": revision, "clock": {"kind": "fixture_offset",
                "anchors": [[0, 1000], [40, 1040]], "uncertainty": 1},
                "environment": "host_model", "expected_count": 3, "tolerance_ticks": 2}
    if mode == "bad_clock":
        manifest["clock"]["anchors"][1][1] = 2040
    if mode == "uncertain_clock":
        manifest["clock"]["uncertainty"] = 3
    save(folder / "manifest.json", manifest)
    scenario = {"run": run_id, "revision": revision, "status": "NOT_RUN", "samples": []}
    capture = {"status": "INCOMPLETE", "cleanup": "UNKNOWN", "exit_code": None}
    events = queue.Queue()
    raw, rows = [], []
    proc = None
    reader = None
    with (folder / "source.stderr").open("wb") as stderr:
        try:
            proc = subprocess.Popen([sys.executable, "-u", str(Path(__file__).with_name("source.py")), mode],
                                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr)
            # Поток читает только pipe; в нём нет GDB API. Размер fixture ограничен протоколом.
            def read_pipe():
                try:
                    for line in proc.stdout:
                        events.put(line)
                finally:
                    events.put(None)
            reader = threading.Thread(target=read_pipe, daemon=True)
            reader.start()
            deadline = time.monotonic() + 3
            def receive():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("capture deadline")
                line = events.get(timeout=remaining)
                if line is None:
                    return None
                raw.append(line)
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("object expected")
                rows.append(row)
                return row
            if receive() != {"kind": "ready", "source": "fixture"}:
                raise ValueError("source not ready")
            capture["ready_ns"] = time.perf_counter_ns()
            # Начало окна разрешено лишь после READY; данные источнику — только идентичность опыта.
            capture["window_start_ns"] = time.perf_counter_ns()
            proc.stdin.write((json.dumps({"run": run_id, "revision": revision}) + "\n").encode())
            proc.stdin.flush()
            proc.stdin.close()
            # Минимальная host-нагрузка: масштабирование трёх входов; ожидания заданы отдельно.
            values = [item * 10 for item in (1, 2, 3)]
            if mode == "scenario_fail":
                values[1] = 99
            checks = [{"name": f"sample-{i}", "actual": value, "expected": expected,
                       "passed": value == expected} for i, (value, expected) in enumerate(zip(values, (10, 20, 30)))]
            scenario.update(status="PASS" if all(c["passed"] for c in checks) else "FAIL", checks=checks,
                            samples=[{"tick": tick, "value": value} for tick, value in zip((10, 20, 30), values)])
            save(folder / "scenario.json", scenario)
            deadline = time.monotonic() + 2
            while receive() is not None:
                if len(rows) > 8:
                    raise ValueError("too many records")
            proc.wait(timeout=max(0.01, deadline - time.monotonic()))
            capture["exit_code"] = proc.returncode
            capture["status"] = "COMPLETE" if proc.returncode == 0 else "INCOMPLETE"
        except (ValueError, OSError, TimeoutError, queue.Empty, subprocess.TimeoutExpired) as error:
            capture["error"] = type(error).__name__ + ": " + str(error)
        finally:
            if proc is not None:
                if proc.poll() is None:
                    proc.kill()
                proc.wait(timeout=3)
                if reader is not None:
                    reader.join(timeout=3)
                # Сохранить остаток pipe после остановки, даже если JSON повреждён.
                while not events.empty():
                    line = events.get_nowait()
                    if line is not None:
                        raw.append(line)
                proc.stdout.close()
                if not proc.stdin.closed:
                    proc.stdin.close()
                capture["exit_code"] = proc.returncode
                capture["cleanup"] = "VERIFIED" if reader is None or not reader.is_alive() else "UNKNOWN"
            capture["closed_ns"] = time.perf_counter_ns()
    save(folder / "scenario.json", scenario)
    scenario_hash = hashlib.sha256((folder / "scenario.json").read_bytes()).hexdigest()
    (folder / "external.jsonl").write_bytes(b"".join(raw))
    save(folder / "capture.json", capture)
    analysis = analyze_files(folder)
    save(folder / "analysis.json", analysis)
    hashes = {name: hashlib.sha256((folder / name).read_bytes()).hexdigest()
              for name in ("manifest.json", "scenario.json", "external.jsonl", "capture.json", "analysis.json")}
    save(folder / "sha256.json", hashes)
    expected_status = "NOT_RUN" if mode == "not_ready" else "FAIL" if mode == "scenario_fail" else "PASS"
    ok = ((analysis["verdict"], analysis["reason"]) == CASES[mode]
          and scenario["status"] == expected_status and capture["cleanup"] == "VERIFIED"
          and hashes["scenario.json"] == scenario_hash)
    return {"case": mode, "scenario": scenario["status"], "capture": capture["status"],
            "analysis": analysis, "cleanup": capture["cleanup"], "ok": ok}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    out = args.output or ROOT / "build/external-capture" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True, exist_ok=False)
    # Ревизия учебных входов — хеш исходников, не выдуманная ревизия прошивки.
    inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob("*.py")}
    (out / "inputs").mkdir()
    for name in inputs:
        (out / "inputs" / name).write_bytes(Path(__file__).with_name(name).read_bytes())
    revision = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    results = []
    summary = {"status": "ERROR", "inputs": inputs, "results": results}
    try:
        for mode in CASES:
            result = capture_one(out / mode, mode, revision)
            results.append(result)
            print(mode, result["analysis"]["verdict"], "OK" if result["ok"] else "MISMATCH")
        summary["status"] = "PASS" if all(r["ok"] for r in results) else "ERROR"
    finally:
        save(out / "summary.json", summary)
        print(out / "summary.json")
    return 0 if summary["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
