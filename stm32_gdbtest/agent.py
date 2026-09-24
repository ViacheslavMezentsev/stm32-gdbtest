"""Explicit GDB entry point; never auto-loaded from ELF."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import traceback

import gdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.target import Target, CheckFailed
from stm32_gdbtest.compatibility import inspect_gdb_api, require_gdb_api
from stm32_gdbtest.identity import check_target
from stm32_gdbtest.image import compare_regions, validate_regions


def main():
    session = json.loads(Path(os.environ["STM32_GDBTEST_RUN"]).read_text(encoding="utf-8"))
    sys.path.insert(1, str(Path(session.get("root", ROOT)).resolve()))
    profile = session["profile"]
    report = {"id": session["test"]["id"], "status": "ERROR", "checks": [],
              "gdb_version": gdb.VERSION, "python_version": sys.version.split()[0],
              "connection_attempted": False}
    connected = False
    target = None
    try:
        for command in ("set pagination off", "set confirm off", "set breakpoint pending off",
                        "set remotetimeout 5", "set python print-stack full"):
            gdb.execute(command)
        image = Path(session["image"]).read_bytes()
        regions = session["load_regions"]
        validate_regions(regions, profile["flash_start"], profile["flash_size"], len(image))
        report["elf_sha256"] = hashlib.sha256(Path(session["elf"]).read_bytes()).hexdigest()
        report["bin_sha256"] = hashlib.sha256(image).hexdigest()
        report["gdb_api_checks"] = inspect_gdb_api(gdb)
        require_gdb_api(report["gdb_api_checks"])
        report["connection_attempted"] = True
        gdb.execute("target extended-remote " + session["endpoint"])
        connected = True
        for command in session.get("setup", []):
            gdb.execute(command)
        gdb.execute(session["reset_halt"])
        inferior = gdb.selected_inferior()
        report["flashed"] = False
        check_target(profile, inferior.read_memory, len(image),
                     session.get("identity_policy", "warn"), report)
        for warning in report.get("warnings", []):
            print("WARNING: " + warning)
        def verify_image():
            results = compare_regions(inferior.read_memory, image, regions,
                                      profile["flash_start"], profile["flash_size"])
            report["image_verification"] = dict(scope="elf-load-sections", bin_gap_fill=255,
                gaps_verified=False, full_region_crc_verified=False, regions=results)
            return all(region["matches"] for region in results)
        matches = verify_image()
        if not matches and session["flash"] == "if-different":
            gdb.execute("load")
            report["flashed"] = True
            matches = verify_image()
        if not matches:
            raise RuntimeError("Flash does not match the selected ELF image")
        report["image_verified"] = True
        target = Target(report, profile)
        target.boot(session["reset_halt"])
        spec = importlib.util.spec_from_file_location("board_test", session["test"]["path"])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        getattr(module, session["test"]["function"])(target)
        report["status"] = "PASS"
    except CheckFailed:
        report.update(status="FAIL", error=traceback.format_exc())
    except BaseException:
        report.update(status="ERROR", error=traceback.format_exc())
    finally:
        if report["status"] != "PASS" and connected:
            diagnostics = report["diagnostics"] = {}
            diagnostic_errors = {}
            for name in profile["core_registers"]:
                try:
                    diagnostics[name] = int(gdb.newest_frame().read_register(name))
                except Exception as exc:
                    diagnostic_errors[name] = str(exc)
            for name, address in profile["diagnostic_registers"].items():
                try:
                    diagnostics[name] = int.from_bytes(
                        gdb.selected_inferior().read_memory(address, 4), "little")
                except Exception as exc:
                    diagnostic_errors[name] = str(exc)
            try:
                report["backtrace"] = gdb.execute("bt", to_string=True)
            except Exception as exc:
                diagnostic_errors["backtrace"] = str(exc)
            if diagnostic_errors:
                report["diagnostic_errors"] = diagnostic_errors
        try:
            if target:
                target.close()
            if connected:
                for command in session["finish"]:
                    gdb.execute(command)
                report["teardown"] = "reset_run"
        except BaseException:
            report.update(status="ERROR", teardown_error=traceback.format_exc())
        Path(session["result"]).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report))
    gdb.execute("quit " + str({"PASS": 0, "FAIL": 1, "ERROR": 2}[report["status"]]))


main()
