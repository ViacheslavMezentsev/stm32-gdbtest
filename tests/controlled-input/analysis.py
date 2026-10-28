"""Независимый анализ кампании; исходный FAIL/ERROR не переписывается."""
import re

EXPECTED = {
    "HW_INPUT_BASELINE": ("PASS", "none", 0, 0, 0, 1),
    "HW_INPUT_SRAM": ("PASS", "sram", 1, 1, 1, 1),
    "HW_INPUT_RET_HIGH": ("PASS", "ret", 1, 1, 1, 0),
    "HW_INPUT_RET_LOW": ("PASS", "ret", 0, 0, 0, 0),
    "HW_INPUT_TOO_EARLY": ("FAIL", "sram-too-early", 1, 0, 0, 1),
    "HW_INPUT_EXCEPTION": ("ERROR", None, None, None, None, None)
}


def assess(name, code, report, records):
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    status, method, supplied, consumed, active, reads = EXPECTED[name]
    require(report.get("id") == name, "scenario identity")
    require(report.get("status") == status and code == {"PASS": 0, "FAIL": 1, "ERROR": 2}[status], "scenario outcome")
    require(report.get("mode") == "emulator" and report.get("image_verified") is True, "verified emulator image")
    require(report.get("cleanup") == "VERIFIED" and report.get("execution_cleanup") == "VERIFIED", "cleanup")
    require(report.get("capture", {}).get("status") == "saved", "capture missing")
    meta = report.get("evidence", {})
    require(bool(meta) and meta.get("diagnostics_total", 0) == 0, "evidence diagnostics")
    require(all(s.get("state") == "complete" for s in meta.get("stores", {}).values()), "incomplete evidence")
    def one(label):
        rows = [r["data"] for r in records if r["name"] == label]
        require(len(rows) == 1, "missing/duplicate " + label)
        return rows[0]
    restoration = one("restoration")
    digest = restoration.get("before_sha256", "")
    require(restoration.get("verified") is True and restoration.get("bytes") == 32
            and re.fullmatch("[0-9a-f]{64}", digest) is not None
            and restoration.get("after_sha256") == digest, "restoration not verified")
    failed = [c["name"] for c in report.get("checks", []) if c.get("passed") is False]
    require(failed == (["ранняя подмена потреблена"] if status == "FAIL" else []), "unexpected failed check")
    if status == "ERROR":
        error = report.get("primary_error", {})
        require(error.get("type") == "RuntimeError" and error.get("message") ==
                "controlled-input: intentional exception before consumption", "unexpected exception")
        require(one("interruption") == {"stage": "before-consumption", "applied": 1}, "interruption evidence")
        require(not any(r["name"] == "observation" for r in records), "unexpected consumption evidence")
    else:
        row = one("observation")
        require(row.get("scope") == "software-input" and row.get("excluded") ==
                ["physical-signal", "peripheral-acquisition"], "evidence scope")
        require([row.get(k) for k in ("method", "supplied", "consumed", "active", "reads", "cycles")] ==
                [method, supplied, consumed, active, reads, 1], "consumption oracle")
    return {"analysis": "PASS", "scenario": status, "scope": "software-input", "restoration": "VERIFIED"}
