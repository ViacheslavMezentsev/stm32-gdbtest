"""Независимый анализ кампании A5.3; исходные FAIL/ERROR не переписываются."""
import re

# Пакеты опыта в шестнадцатеричном виде, как их сохраняет сценарий.
A, B, BAD = "5f21030304058f", "5f2201098b", "5f210303040590"
# Сценарий: ожидаемый исход, метод, пакеты, возвраты обработчика и счётчики
# (accepted, rejected, sequence, last_type, last_sum, entries, busy) в момент наблюдения.
EXPECTED = {
    "HW_BUFFER_BASELINE": ("PASS", "none", [], [], (1, 0, 1, 0x10, 3, 1, 0)),
    "HW_BUFFER_PACKETS": ("PASS", "buffer-call", [A, B], [1, 1], (2, 0, 2, 0x22, 9, 2, 0)),
    "HW_BUFFER_REJECT": ("PASS", "buffer-call", [BAD, A], [0, 1], (1, 1, 1, 0x21, 12, 2, 0)),
    "HW_BUFFER_REENTRY": ("PASS", "buffer-call-reentry", [A], [0], (0, 1, 0, 0, 0, 2, 1)),
    "HW_BUFFER_BOUNDS": ("PASS", "buffer-call-refused", [A], [], (0, 0, 0, 0, 0, 0, 0)),
    "HW_BUFFER_UNCONSUMED": ("FAIL", "buffer-write-only", [A], [], (1, 0, 1, 0x10, 3, 1, 0)),
    "HW_BUFFER_EXCEPTION": ("ERROR", None, None, None, None)
}
COUNTERS = ("accepted", "rejected", "sequence", "last_type", "last_sum", "entries", "busy")
EXCLUDED = ["dma", "peripheral-acquisition", "interrupt-context", "physical-signal"]
SECTION_BYTES = 76


def assess(name, code, report, records):
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    status, method, packets, returned, counters = EXPECTED[name]
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
    require(restoration.get("verified") is True and restoration.get("bytes") == SECTION_BYTES
            and re.fullmatch("[0-9a-f]{64}", digest) is not None
            and restoration.get("after_sha256") == digest, "restoration not verified")
    checks = report.get("checks", [])
    failed = [c["name"] for c in checks if c.get("passed") is False]
    require(failed == (["пакет опыта потреблён"] if status == "FAIL" else []), "unexpected failed check")
    if name == "HW_BUFFER_BOUNDS":
        refusal = [c for c in checks if c.get("name") == "Pointer за границей массива"]
        require(len(refusal) == 1 and refusal[0].get("passed") is True, "early refusal missing")
    if status == "ERROR":
        error = report.get("primary_error", {})
        require(error.get("type") == "RuntimeError" and error.get("message") ==
                "buffer-consumption: intentional exception before call", "unexpected exception")
        require(one("interruption") == {"stage": "before-call", "bytes": 7}, "interruption evidence")
        require(not any(r["name"] == "observation" for r in records), "unexpected consumption evidence")
    else:
        row = one("observation")
        require(row.get("scope") == "software-buffer" and row.get("excluded") == EXCLUDED, "evidence scope")
        require(row.get("method") == method and row.get("packets") == packets and row.get("returned") == returned,
                "delivery evidence")
        require(tuple(row.get(k) for k in COUNTERS) == counters, "consumption oracle")
    return {"analysis": "PASS", "scenario": status, "scope": "software-buffer", "restoration": "VERIFIED"}
