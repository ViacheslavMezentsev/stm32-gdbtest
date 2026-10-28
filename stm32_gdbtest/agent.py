"""Explicit GDB entry point; never auto-loaded from ELF."""

import inspect
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

import gdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest import arch
from stm32_gdbtest.target import Target, CheckFailed
from stm32_gdbtest.errors import error_summary
from stm32_gdbtest.compatibility import inspect_gdb_api, require_gdb_api
from stm32_gdbtest.identity import check_target
from stm32_gdbtest.image import compare_regions, validate_regions
from stm32_gdbtest.full_image import compare_full, validate_image
from stm32_gdbtest.config_transport import loads
from stm32_gdbtest.configuration import thaw
from stm32_gdbtest.result_capture import save as save_records
from stm32_gdbtest.scenario import ScenarioSkipped, invoke, invoke_async
from stm32_gdbtest.reports import CODES
from stm32_gdbtest import report_data


async def main():
    started = time.monotonic()
    session = json.loads(Path(os.environ["STM32_GDBTEST_RUN"]).read_text(encoding="utf-8"))
    sys.path.insert(1, str(Path(session.get("root", ROOT)).resolve()))
    profile = session["profile"]
    emulator = session.get("environment") == "emulator"
    report = {"id": session["test"]["id"], "status": "ERROR", "checks": [],
              "gdb_version": gdb.VERSION, "python_version": sys.version.split()[0],
              "connection_attempted": False}
    report["run_id"] = session.get("run_id", Path(session["result"]).parent.name)
    configuration = None
    completion = "unknown"
    connected = False
    target = None
    adapter = arch.adapter(session.get("arch"))
    try:
        configuration = loads(session['configuration']) if session.get('configuration') else None
        if configuration and (thaw(configuration.config['target']) != profile or
                (thaw(configuration.config['image']['image']) if configuration.config['image'] else None)
                != session.get('full_image_policy')):
            raise ValueError('Configuration differs from prepared profile/image')
        for command in ("set pagination off", "set confirm off", "set breakpoint pending off",
                        "set remotetimeout 5", "set python print-stack full"):
            gdb.execute(command)
        image = Path(session["image"]).read_bytes()
        regions = session["load_regions"]
        full_policy = session.get("full_image_policy")
        if full_policy:
            validate_image(image, regions, full_policy, profile)
            program_elf = Path(session["program_elf"])
            if hashlib.sha256(program_elf.read_bytes()).hexdigest() != session["program_elf_sha256"]:
                raise ValueError("Programming ELF differs from host snapshot")
        else:
            validate_regions(regions, profile["flash_start"], profile["flash_size"], len(image))
        report["elf_sha256"] = hashlib.sha256(Path(session["elf"]).read_bytes()).hexdigest()
        report["bin_sha256"] = hashlib.sha256(image).hexdigest()
        if report["bin_sha256"] != session["expected_bin_sha256"]:
            raise ValueError("BIN differs from host snapshot")
        report["gdb_api_checks"] = inspect_gdb_api(gdb)
        require_gdb_api(report["gdb_api_checks"])
        report["connection_attempted"] = True
        gdb.execute(("target remote " if emulator else "target extended-remote ") + session["endpoint"])
        connected = True
        for command in session.get("setup", []):
            gdb.execute(command)
        if session["reset_halt"] is not None:
            gdb.execute(session["reset_halt"])
        inferior = gdb.selected_inferior()
        report["flashed"] = False
        if emulator:
            if len(inferior.threads()) != 1:
                raise RuntimeError('Emulator backend requires exactly one CPU thread')
            if not gdb.selected_thread() or not gdb.selected_thread().is_stopped():
                raise RuntimeError('Emulator CPU is not halted')
            report['identity_verification'] = 'emulator-model; no hardware identity claimed'
        else:
            check_target(profile, inferior.read_memory, len(image),
                         session.get("identity_policy", "warn"), report)
        for warning in report.get("warnings", []):
            print("WARNING: " + warning)
        def verify_image():
            if full_policy:
                report["image_verification"] = compare_full(inferior.read_memory, image, full_policy, profile)
                return report["image_verification"]["full_region_crc_verified"]
            results = compare_regions(inferior.read_memory, image, regions,
                                      profile["flash_start"], profile["flash_size"])
            report["image_verification"] = dict(scope="elf-load-sections", bin_gap_fill=255,
                gaps_verified=False, full_region_crc_verified=False, regions=results)
            return all(region["matches"] for region in results)
        matches = verify_image()
        if not matches and session["flash"] == "if-different":
            report["image_before_programming"] = report["image_verification"]
            gdb.execute("load " + json.dumps(program_elf.as_posix()) if full_policy else "load")
            if full_policy:
                gdb.execute("symbol-file " + json.dumps(Path(session["elf"]).as_posix()))
            report["flashed"] = True
            matches = verify_image()
        if not matches:
            raise RuntimeError("Flash does not match the selected ELF image")
        report["image_verified"] = True
        case = {key: session["test"][key] for key in ("id", "function", "timeout_s", "labels", "contracts")
                if key in session["test"]}
        target = Target(report, profile, configuration,
                        context=dict(case=case, stand=session.get("stand_info"), build=session.get("build_info"),
                                     reset_halt=session["reset_halt"]))
        target.boot(session["reset_halt"], guards=adapter.fault_guards(profile))
        spec = importlib.util.spec_from_file_location("board_test", session["test"]["path"])
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        completion = "interrupted"
        function = getattr(module, session["test"]["function"])
        if inspect.iscoroutinefunction(function):
            from stm32_gdbtest.execution import LiveExecution
            target._execution = LiveExecution(target, gdb)
            target._deadline = started + max(0, case["timeout_s"] - 2.0)
            await invoke_async(function, target)
            target._assert_awaited()
        else:
            invoke(function, target)
        completion = "normal"
        report["status"] = "PASS"
    except ScenarioSkipped as exc:
        report.update(status="SKIP", skip_reason=str(exc))
    except CheckFailed as exc:
        report.update(status="FAIL", error=traceback.format_exc(), primary_error=error_summary(exc))
    except BaseException as exc:
        report.update(status="ERROR", error=traceback.format_exc(), primary_error=error_summary(exc))
        if getattr(exc, 'details', {}).get('audit_error') is not None:
            report['audit_error'] = exc.details['audit_error']
        if exc.__cause__ is not None:
            report['primary_cause'] = error_summary(exc.__cause__)
    finally:
        # Stop before diagnostics/capture/teardown; preserve the body error independently.
        execution = getattr(target, '_execution', None)
        if target is not None:
            target._unawaited = None
        if execution is not None:
            try:
                await execution.cleanup()
                report['execution_cleanup'] = 'VERIFIED'
            except BaseException:
                report.update(status_before_execution_cleanup=report['status'], status='ERROR',
                              execution_cleanup='ERROR', execution_cleanup_error=traceback.format_exc())
        if report.get('report_audit_error_count') and report['status'] == 'PASS':
            report.update(status_before_report_audit='PASS', status='ERROR')
        parameter_errors = getattr(gdb, '_stm32_parameter_cleanup_errors', [])
        if parameter_errors:
            report.update(status_before_parameter_cleanup=report['status'], status='ERROR',
                          parameter_cleanup_errors=parameter_errors)
        if configuration and configuration.capture_results:
            save_records(Path(session["result"]).parent, report, target, completion)
        if report["status"] != "PASS" and connected and (execution is None or execution.state() == "stopped"):
            diagnostics = report["diagnostics"] = {}
            diagnostic_errors = {}
            for name in adapter.diagnostic_registers(profile):
                try:
                    diagnostics[name] = int(gdb.newest_frame().read_register(name))
                except Exception as exc:
                    diagnostic_errors[name] = str(exc)
            for name, address in adapter.diagnostic_memory(profile).items():
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
            if connected and report.get("execution_cleanup") != "ERROR":
                for command in session["finish"]:
                    gdb.execute(command)
                report["teardown"] = "disconnected" if emulator else "reset_run"
        except BaseException:
            report.update(status="ERROR", teardown_error=traceback.format_exc())
        # A value a scenario put into its checks must not cost the whole report: it is kept as its repr.
        try:
            report_data.write(session['result'], report)
            output = (report_data.summary(report) if report.get('report_policy', {}).get('console') in ('failures', 'summary')
                      else report_data.payload(report, False))
            print(json.dumps(output, default=repr))
        except Exception as cause:
            fallback = {k:v for k,v in report.items() if k not in report_data.COLLECTIONS}
            fallback.update(report_storage_error=error_summary(cause), checks=[])
            report_data.write(session['result'], fallback, compact=False)
            print(json.dumps(report_data.summary(fallback), default=repr))
        finally:
            report_data.close(report)
    gdb.execute("quit " + str(CODES[report["status"]]))


from stm32_gdbtest.execution import CoroutineRunner

def scheduler_failed(error):
    traceback.print_exception(type(error), error, error.__traceback__)
    gdb.execute('quit 2')

CoroutineRunner(main(), gdb, scheduler_failed).start()
