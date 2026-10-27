"""Подставной внешний процесс: отдельный канал, без чтения результата сценария."""
import json
import sys
import time


def emit(row):
    print(json.dumps(row), flush=True)


def main():
    mode = sys.argv[1]
    if mode == "not_ready":
        return 0
    emit({"kind": "ready", "source": "fixture"})
    request = json.loads(sys.stdin.readline())
    if mode == "timeout":
        time.sleep(60)
        return 0
    rows = []
    # Отдельный предзаданный поток: источник не копирует result/records сценария.
    for seq, (tick, value) in enumerate(((10, 10), (20, 20), (30, 30))):
        rows.append({"kind": "sample", "run": request["run"], "revision": request["revision"],
                     "source": "fixture", "channel": "signal", "unit": "unit", "seq": seq,
                     "source_tick": tick + 1000, "value": value})
    if mode == "drop":
        rows.pop(1)
    if mode == "duplicate":
        rows.insert(1, dict(rows[0]))
    if mode == "reorder":
        rows[0], rows[1] = rows[1], rows[0]
    if mode == "wrong_run":
        rows[1]["run"] = "other-run"
    if mode == "wrong_revision":
        rows[1]["revision"] = "other-revision"
    if mode == "wrong_unit":
        rows[1]["unit"] = "other-unit"
    if mode == "wrong_channel":
        rows[1]["channel"] = "other-channel"
    if mode == "mismatch":
        rows[1]["value"] = 99
    if mode == "time_violation":
        rows[1]["source_tick"] += 4
    if mode == "time_boundary":
        rows[1]["source_tick"] += 2
    for row in rows:
        emit(row)
    if mode == "truncated":
        print('{"kind":', flush=True)
        return 0
    if mode == "no_end":
        return 0
    emit({"kind": "end", "run": request["run"], "count": len(rows)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
