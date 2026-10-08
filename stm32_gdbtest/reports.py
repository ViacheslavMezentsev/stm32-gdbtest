import json
from pathlib import Path
import xml.etree.ElementTree as ET


CODES = {"PASS": 0, "FAIL": 1, "ERROR": 2, "SKIP": 77}


def write_reports(directory, report):
    directory = Path(directory)
    (directory / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    status = report["status"]
    artifact = report.get("artifact_error")
    suite = ET.Element("testsuite", name="hwtest", tests=str(1 + int(bool(artifact))),
                       failures=str(int(status == "FAIL")), errors=str(int(status == "ERROR") + int(bool(artifact))),
                       time=str(report["duration_s"]))
    case = ET.SubElement(suite, "testcase", classname="blackpill", name=report["id"],
                         time=str(report["duration_s"]))
    suite.set("skipped", str(int(status == "SKIP")))
    if status == "SKIP":
        ET.SubElement(case, "skipped", message=report["skip_reason"])
    elif status != "PASS":
        node = ET.SubElement(case, "failure" if status == "FAIL" else "error", message=status)
        node.text = report.get("error", "") + "\n" + report.get("teardown_error", "")
    ET.SubElement(case, "system-out").text = json.dumps(report, indent=2)
    if artifact:
        infrastructure = ET.SubElement(suite, "testcase", classname="infrastructure",
                                       name=report["id"] + ".capture", time="0")
        node = ET.SubElement(infrastructure, "error", message=artifact["message"], type=artifact["type"])
        node.text = json.dumps(report.get("capture", {}), indent=2)
    ET.ElementTree(suite).write(directory / "junit.xml", encoding="utf-8", xml_declaration=True)
