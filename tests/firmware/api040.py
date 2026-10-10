"""Prepare and run only the API 0.4.0 example campaign; no firmware rebuild on the stand."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.configuration import capture

IDS = ("HW_CI_040_RECORDS", "HW_CI_040_SKIP", "HW_CI_040_SKIP_VALIDATION", "HW_CI_040_STRING_VIEWS")


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def command(arguments, log):
    with log.open("w", encoding="utf-8") as stream:
        return subprocess.run([sys.executable, "-X", "utf8", "-B", "-m", "stm32_gdbtest", *map(str, arguments)],
                              cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=300).returncode


def prepare(session_path, output):
    """Capture explicit enabled/disabled configurations before packing; never patch an extracted capsule."""
    session = json.loads(session_path.read_text(encoding="utf-8"))
    config = capture(session)
    source_api = config._source_bytes["api"].decode("utf-8")
    if "release040" in tomllib.loads(source_api).get("user", {}):
        raise ValueError("The fixture api.toml already defines user.release040")
    output.mkdir(parents=True, exist_ok=False)
    for enabled in (True, False):
        name = "enabled" if enabled else "disabled"
        folder = output / name
        folder.mkdir()
        api = source_api + "\n[user.release040]\noptional_loop = " + str(enabled).lower() + "\n"
        (folder / "api.toml").write_text(api, encoding="utf-8")
        (folder / "session.toml").write_text(
            "[config]\ntarget = " + json.dumps(str(Path(session["profile"]).resolve()))
            + '\napi = "api.toml"\n\n[results]\ncapture = true\n', encoding="utf-8")
        descriptor = dict(session, session_config=str(folder / "session.toml"), out=str(folder / "prepare"))
        write_json(folder / "session.json", descriptor)
        arguments = ["pack", "--session", folder / "session.json", "--output", output / (name + ".zip")]
        for identifier in IDS if enabled else ("HW_CI_040_SKIP",):
            arguments.extend(("--test", identifier))
        if command(arguments, folder / "pack.log"):
            raise RuntimeError("Package preparation failed: " + str(folder / "pack.log"))


def validate_run(path, code, identifier, enabled):
    """Unexpected SKIP, missing capture, bad teardown and corrupt evidence all reject the campaign."""
    report = json.loads(path.read_text(encoding="utf-8"))
    skipped = identifier == "HW_CI_040_SKIP" and not enabled
    if (code, report.get("command_code"), report.get("status")) != ((77, 77, "SKIP") if skipped else (0, 0, "PASS")):
        raise ValueError("Unexpected command/scenario outcome")
    if report.get("image_verified") is not True or report.get("teardown") != "reset_run":
        raise ValueError("Image verification or teardown not confirmed")
    checks = report.get("checks", [])
    if not checks or any(row.get("passed") is not True for row in checks):
        raise ValueError("Missing or unsuccessful checks")
    capture_info = report.get("capture", {})
    if (capture_info.get("status"), capture_info.get("completion")) != ("saved", "interrupted" if skipped else "normal"):
        raise ValueError("Capture not confirmed")
    raw = path.with_name("records.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != capture_info.get("sha256"):
        raise ValueError("Records digest differs")
    document = json.loads(raw)
    records = document["records"]
    if (document["case_id"], document["run_id"], len(records)) != (identifier, report["run_id"], capture_info["count"]):
        raise ValueError("Records do not belong to this run")
    xml = ET.parse(path.with_name("junit.xml"))
    skips = list(xml.iter("skipped"))
    if len(skips) != int(skipped) or list(xml.iter("error")) or list(xml.iter("failure")):
        raise ValueError("JUnit outcome differs")
    if skipped and (not report.get("skip_reason") or skips[0].get("message") != report["skip_reason"]):
        raise ValueError("Skip reason differs")
    if identifier == "HW_CI_040_SKIP":
        names = [row["name"] for row in records]
        expected = (["capability", "optional.finally"] if skipped else
                    ["capability", "optional.executed", "optional.finally", "optional.completed"])
        if names != expected:
            raise ValueError("SKIP control-flow evidence differs")
    if identifier == "HW_CI_040_RECORDS":
        payload = records[-1]["data"]["payload"]
        if not (type(payload["zero"]) is int and payload["zero"] == 0 and payload["enabled"] is False
                and payload["missing"] is None and type(payload["large"]) is int and payload["large"] == 2**60 + 1):
            raise ValueError("Mixed record types differ")
    return report


def run(enabled_package, disabled_package, stand, output):
    output.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S-"), dir=output))
    summary = dict(status="RUNNING", runs=[], processing={})
    selection = dict(schema=1, name="API 0.4.0: " + stand.stem, runs=[])
    try:
        for enabled, package in ((True, enabled_package), (False, disabled_package)):
            for identifier in IDS if enabled else ("HW_CI_040_SKIP",):
                label = ("enabled-" if enabled else "disabled-") + identifier
                workdir = folder / label
                code = command(["run", "--package", package, "--workdir", workdir,
                                "--test", identifier, "--stand", stand], folder / (label + ".log"))
                reports = list(workdir.rglob("result.json"))
                if len(reports) != 1:
                    raise ValueError("Missing unique result for " + label)
                path = reports[0]
                row = dict(id=identifier, enabled=enabled, code=code, result=path.relative_to(folder).as_posix())
                summary["runs"].append(row)
                selection["runs"].append(dict(result=row["result"], stand=stand.stem,
                    artifacts={"junit": path.with_name("junit.xml").relative_to(folder).as_posix()}))
                report = validate_run(path, code, identifier, enabled)
                row["status"] = report["status"]
                write_json(folder / "summary.json", summary)
                print(label, report["status"], flush=True)
        summary["status"] = "PASS"
    except Exception as error:
        summary.update(status="ERROR", error=str(error))
    finally:
        write_json(folder / "selection.json", selection)
        # Process partial campaigns too; evidence-tool success never changes a rejected hardware outcome.
        if selection["runs"]:
            for name, args in (
                ("export", ["export", "--selection", folder / "selection.json", "--output", folder / "export"]),
                ("verify", ["verify", "--index", folder / "export/index.json", "--output", folder / "integrity.json"]),
                ("report", ["report", "--index", folder / "export/index.json", "--export", folder / "export/export.json",
                            "--output", folder / "report"])):
                try:
                    summary["processing"][name] = command(["results", *args, "--root", folder], folder / (name + ".log"))
                except Exception as error:
                    summary["processing"][name] = str(error)
            if any(value != 0 for value in summary["processing"].values()):
                summary["status"] = "ERROR"
        summary["passed"] = sum(row.get("status") == "PASS" for row in summary["runs"])
        summary["skipped"] = sum(row.get("status") == "SKIP" for row in summary["runs"])
        write_json(folder / "summary.json", summary)
    print("API040:", folder / "summary.json", flush=True)
    return 0 if summary["status"] == "PASS" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    pack = sub.add_parser("pack")
    pack.add_argument("--session", type=Path, required=True)
    pack.add_argument("--output", type=Path, required=True)
    execute = sub.add_parser("run")
    execute.add_argument("--enabled-package", type=Path, required=True)
    execute.add_argument("--disabled-package", type=Path, required=True)
    execute.add_argument("--stand", type=Path, required=True)
    execute.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.action == "pack":
        prepare(args.session.resolve(), args.output.resolve())
        return 0
    return run(args.enabled_package.resolve(), args.disabled_package.resolve(), args.stand.resolve(), args.output.resolve())


if __name__ == "__main__":
    sys.exit(main())
