import json
from pathlib import Path
import xml.etree.ElementTree as ET
from stm32_gdbtest import report_data


CODES = {"PASS": 0, "FAIL": 1, "ERROR": 2, "SKIP": 77}


def write_reports(directory, report):
    directory = Path(directory)
    try:
        report_data.write(directory / 'result.json', report)
    except Exception as cause:
        report['report_storage_error'] = dict(type=type(cause).__name__, message=str(cause))
        report['command_code'] = 2
        fallback = {k:v for k,v in report.items() if k not in report_data.COLLECTIONS}
        fallback['checks'] = []
        report_data.write(directory / 'result.json', fallback, compact=False)
    output_report = fallback if "fallback" in locals() else report
    status = report["status"]
    artifact = report.get("artifact_error") or report.get("report_storage_error")
    if not artifact and report.get("report_audit_error_count"):
        artifact = dict(type="ReportAuditError", message="Completed report evidence is incomplete")
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
    output = (report_data.summary(output_report) if report.get('report_policy', {}).get('console') == 'failures'
              else report_data.payload(output_report, False))
    ET.SubElement(case, "system-out").text = json.dumps(output, indent=2)
    if artifact:
        infrastructure = ET.SubElement(suite, "testcase", classname="infrastructure",
                                       name=report["id"] + (".capture" if report.get("artifact_error") else ".report"), time="0")
        node = ET.SubElement(infrastructure, "error", message=artifact["message"], type=artifact["type"])
        node.text = json.dumps(report.get("capture", {}), indent=2)
    ET.ElementTree(suite).write(directory / "junit.xml", encoding="utf-8", xml_declaration=True)
