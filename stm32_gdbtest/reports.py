import json
from pathlib import Path
import xml.etree.ElementTree as ET


CODES = {"PASS": 0, "FAIL": 1, "ERROR": 2}


def write_reports(directory, report):
    directory = Path(directory)
    (directory / "result.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    status = report["status"]
    suite = ET.Element("testsuite", name="hwtest", tests="1",
                       failures=str(int(status == "FAIL")), errors=str(int(status == "ERROR")),
                       time=str(report["duration_s"]))
    case = ET.SubElement(suite, "testcase", classname="blackpill", name=report["id"],
                         time=str(report["duration_s"]))
    if status != "PASS":
        node = ET.SubElement(case, "failure" if status == "FAIL" else "error", message=status)
        node.text = report.get("error", "") + "\n" + report.get("teardown_error", "")
    ET.SubElement(case, "system-out").text = json.dumps(report, indent=2)
    ET.ElementTree(suite).write(directory / "junit.xml", encoding="utf-8", xml_declaration=True)
