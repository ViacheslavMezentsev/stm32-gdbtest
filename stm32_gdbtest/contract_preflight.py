"""Executed in a separate batch GDB before the debug server is started."""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

import gdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stm32_gdbtest.contracts import inspect_contracts

request = json.loads(Path(os.environ["STM32_GDBTEST_CONTRACT_REQUEST"]).read_text(encoding="utf-8"))
try:
    report = inspect_contracts(gdb, request["selected"])
except BaseException:
    report = dict(schema=1, status="ERROR", error=traceback.format_exc())
report["elf_sha256"] = hashlib.sha256(Path(request["elf"]).read_bytes()).hexdigest()
report["gdb_version"] = gdb.VERSION
report["connection_attempted"] = False
Path(request["result"]).write_text(json.dumps(report, indent=2), encoding="utf-8")
gdb.execute("quit " + ("0" if report["status"] == "PASS" else "2"))
