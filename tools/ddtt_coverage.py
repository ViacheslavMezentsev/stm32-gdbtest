"""Export explicitly mapped DDTT check evidence as LCOV (no target access)."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import sys
try:
    from .ddtt_guard import validate_point
    from . import ddtt_qualification as qualification
except ImportError:
    from ddtt_guard import validate_point
    import ddtt_qualification as qualification


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def validate(mapping):
    if type(mapping.get("schema", 1)) is not int or mapping.get("schema", 1) not in (1, 2) or not isinstance(mapping.get("points"), list):
        raise ValueError("Expected map schema 1/2 and points array")
    if mapping.get("environment", "hardware") not in ("hardware", "emulator", "host"):
        raise ValueError("Invalid evidence environment")
    for entry in [mapping, *mapping["points"]]:
        key = "elf_sha256" if entry is mapping else "source_sha256"
        if not re.fullmatch(r"[0-9a-f]{64}", entry.get(key, "")):
            raise ValueError("Invalid " + key)
    for point in mapping["points"]:
        for key in ("source", "anchor", "scenario", "check"):
            value = point.get(key)
            if not isinstance(value, str) or not value.strip() or any(c in value for c in "\r\n"):
                raise ValueError("Invalid point " + key)
        path = Path(point["source"])
        if path.is_absolute() or ".." in path.parts or "\\" in point["source"] or ":" in point["source"]:
            raise ValueError("source must be a project-relative POSIX path")

    qualification.validate(mapping)

def project(root, mapping, results):
    """Latest selected automated attempt wins, including incompatible/error attempts."""
    validate(mapping)
    root = Path(root).resolve()
    by_case = defaultdict(list)
    for path in sorted(set(Path(p).resolve() for p in results)):
        data = load(path)
        if data.get("mode") != mapping.get("environment", "hardware") or data.get("purpose", "automated") != "automated":
            continue
        stamp = datetime.fromisoformat(data["started_utc"].replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            raise ValueError("Result timestamp needs a timezone: " + str(path))
        by_case[data["id"]].append((stamp, data, path))
    rows = []
    for point in mapping["points"]:
        source = (root / point["source"]).resolve()
        if not source.is_relative_to(root) or any(c in source.as_posix() for c in "\r\n"):
            raise ValueError("source outside project or invalid LCOV path")
        if digest(source) != point["source_sha256"]:
            raise ValueError("source changed: " + point["source"])
        matches = [validate_point(root, point)]
        if len(matches) != 1:
            raise ValueError("Source anchor must match exactly one line: " + point["anchor"])
        row = dict(point, absolute_source=source.as_posix(), line=matches[0], state="UNKNOWN",
                   reason="no eligible attempt", evidence=None)
        candidates = sorted(by_case[point["scenario"]], key=lambda item: item[0])
        if candidates:
            stamp, data, path = candidates[-1]
            row["evidence"] = dict(path=path.as_posix(), sha256=digest(path),
                                   run_id=data.get("run_id"), status=data.get("status"))
            inputs = data.get("build_manifest", {}).get("inputs", [])
            checks = [c for c in data.get("checks", []) if c.get("name") == point["check"]]
            if sum(item[0] == stamp for item in candidates) != 1:
                row["reason"] = "ambiguous latest attempt"
            elif data.get("elf_sha256") != mapping["elf_sha256"]:
                row["reason"] = "ELF mismatch"
            elif [i.get("sha256") for i in inputs if i.get("file") == point["source"]] != [point["source_sha256"]]:
                row["reason"] = "source manifest mismatch"
            elif data.get("status") not in ("PASS", "FAIL"):
                row["reason"] = "scenario is not PASS/FAIL"
            elif not checks or any(type(c.get("passed")) is not bool for c in checks):
                row["reason"] = "missing or invalid check verdict"
            else:
                row.update(state="CONFIRMED" if all(c["passed"] for c in checks) else "FAILED",
                           reason="executed check", verdicts=[c["passed"] for c in checks])
        if mapping.get("schema", 1) == 2:
            qualification.apply(mapping, point, data if candidates else {}, path if candidates else None, row)
        rows.append(row)
    return rows


def render(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["absolute_source"], row["line"])].append(row["state"])
    files = defaultdict(dict)
    for (source, line), states in grouped.items():
        if "FAILED" in states:
            files[source][line] = 0
        elif "UNKNOWN" not in states:
            files[source][line] = 1
    lines = ["TN:DDTT_check_evidence"]
    for path, marks in sorted(files.items()):
        lines += ["SF:" + path] + ["DA:%d,%d" % pair for pair in sorted(marks.items())]
        lines += ["LF:" + str(len(marks)), "LH:" + str(sum(marks.values())), "end_of_record"]
    return "\n".join(lines) + "\n"


def export(root, mapping, results, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    # Invalidate previous evidence before validation; an error must not leave old green marks.
    (out / "lcov.info").write_text("", encoding="utf-8")
    sidecar = out / "ddtt-evidence.json"
    sidecar.write_text(json.dumps({"schema": 1, "status": "ERROR", "points": []}), encoding="utf-8")
    rows = project(root, mapping, results)
    report = dict(schema=1, status="EXPORTED", interpretation="DDTT check evidence; DA is a Boolean verdict",
                  elf_sha256=mapping["elf_sha256"], summary=dict(Counter(r["state"] for r in rows)), points=rows)
    if mapping.get("schema", 1) == 2:
        report["schema"] = 2
        report["acceptance"] = qualification.summary(rows)
    sidecar.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "lcov.info").write_text(render(rows), encoding="utf-8", newline="\n")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("project", "map", "runs", "out"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        # Load inside export's validation boundary so even malformed JSON clears old output.
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "lcov.info").write_text("", encoding="utf-8")
        (out / "ddtt-evidence.json").write_text('{"schema":1,"status":"ERROR","points":[]}', encoding="utf-8")
        if not Path(args.runs).is_dir():
            raise ValueError("runs directory does not exist")
        rows = export(args.project, load(args.map), Path(args.runs).glob("*/result.json"), out)
        print(json.dumps(dict(Counter(r["state"] for r in rows))))
        return 0  # Export success is separate from scenario/check verdicts.
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
        print("DDTT export error: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
