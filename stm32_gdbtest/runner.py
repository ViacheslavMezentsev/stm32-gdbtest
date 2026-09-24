"""Host orchestrator: snapshot, probe ownership, lifecycle and reports."""

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import time
import traceback

from stm32_gdbtest.backends import load_stand, server_spec
from stm32_gdbtest.profile import load_profile
from stm32_gdbtest.processes import FLAGS, probe_lock, stop_tree
from stm32_gdbtest.reports import CODES, write_reports
from stm32_gdbtest.compatibility import runtime_manifest
from stm32_gdbtest.build_manifest import load_verified
from stm32_gdbtest.contracts import select_contracts
from stm32_gdbtest.image import parse_sections, validate_regions


ROOT = Path(__file__).resolve().parents[1]


def local_directory(path, root=ROOT):
    path = Path(path).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("Output directories must remain inside the selected project root")
    path.mkdir(parents=True, exist_ok=True)
    return path


def run(session, test, stand_path=None, timeout=None, identity_policy=None):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    project_root = Path(session.get("root", ROOT)).resolve()
    out = local_directory(Path(session["out"]) / f"{stamp}-{test['id']}-{os.getpid()}", project_root)
    started = time.monotonic()
    report = {"id": test["id"], "status": "ERROR", "checks": [], "started_utc": stamp}
    try:
        legacy = [name for name in ("HWTEST_STAND", "HWTEST_IDENTITY_POLICY") if os.environ.get(name)]
        if legacy:
            raise ValueError("Rename legacy environment variables to STM32_GDBTEST_: " + ", ".join(legacy))
        policy = identity_policy or os.environ.get("STM32_GDBTEST_IDENTITY_POLICY", "warn")
        if policy not in ("warn", "strict"):
            raise ValueError("Identity policy must be warn or strict")
        session = dict(session, identity_policy=policy)
        report["identity_policy"] = policy
        if os.name != "nt":
            raise RuntimeError("This MVP supports Windows only")
        limit = test["timeout_s"] if timeout is None else timeout
        if not math.isfinite(limit) or not 0 < limit <= 300:
            raise ValueError("Timeout must be positive and <= 300 seconds")
        path = stand_path or os.environ.get("STM32_GDBTEST_STAND") or session.get("stand")
        if not path:
            raise RuntimeError("Select a local stand with STM32_GDBTEST_STAND or --stand")
        stand = load_stand(path)
        report["backend"] = stand["backend"]
        profile = load_profile(session["profile"])
        report["profile"] = profile
        with probe_lock(project_root, stand["serial"], stand["backend"]):
            execute(session, test, stand, out, report, limit, profile)
    except BaseException:
        report.update(status="ERROR", error=traceback.format_exc())
    server_log = ""
    try:
        server_log = (out / "server.log").read_text(encoding="utf-8", errors="replace")
    except OSError:
        pass  # Runs failing before server startup still receive an explicit partial manifest.
    report["compatibility"] = runtime_manifest(report, server_log)
    report["duration_s"] = round(time.monotonic() - started, 3)
    write_reports(out, report)
    for warning in report.get("warnings", []):
        print("WARNING: " + warning)
    print(f"{report['status']} {test['id']}: {out / 'result.json'}")
    if report["status"] != "PASS":
        print(report.get("error", "") + report.get("teardown_error", ""))
    return CODES[report["status"]]


def execute(session, test, stand, out, report, timeout, profile):
    server = client = None
    ready = False
    env = os.environ.copy()
    project_root = Path(session.get("root", ROOT)).resolve()
    temp = local_directory(project_root / "build/hwtest-tmp", project_root)
    env.update(TEMP=str(temp), TMP=str(temp), PYTHONDONTWRITEBYTECODE="1")
    # The embedded Python must not inherit another Python installation's runtime path.
    env.pop("PYTHONHOME", None)
    env.pop("PYTHONPATH", None)
    elf = out / "firmware.elf"
    image = out / "image.bin"
    agent_result = out / "agent-result.json"
    gdb = Path(session["gdb"])
    gdb_base = [str(gdb), "-nx", "-batch", "-q", "-iex", "set auto-load off"]
    endpoint = None
    try:
        # All clients consume this immutable per-run snapshot, never a changing build ELF.
        elf.write_bytes(Path(session["elf"]).read_bytes())
        report["elf_sha256"] = hashlib.sha256(elf.read_bytes()).hexdigest()
        if session.get("build_manifest"):
            manifest = load_verified(session["build_manifest"], report["elf_sha256"], session["profile"])
            report["build_manifest"] = manifest
            (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        names = test.get("contracts", [])
        report["contracts"] = dict(schema=1, requested=names, status="ERROR" if names else "NOT_REQUESTED")
        selected = select_contracts(Path(session["profile"]).parent / "Tests/contracts.json",
                                    names, report.get("build_manifest"))
        if names:
            report["contracts"].update(status="ERROR", selected=selected)
            request = out / "contract-request.json"
            result = out / "contract-result.json"
            request.write_text(json.dumps(dict(elf=str(elf), result=str(result), selected=selected)), encoding="utf-8")
            env["STM32_GDBTEST_CONTRACT_REQUEST"] = str(request)
            with (out / "contract-preflight.log").open("wb") as log:
                preflight = subprocess.run(gdb_base + [str(elf), "-x", str(ROOT / "stm32_gdbtest/contract_preflight.py")],
                    timeout=15, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=FLAGS)
            evidence = json.loads(result.read_text(encoding="utf-8"))
            report["contracts"].update(evidence)
            if (preflight.returncode != 0 or evidence.get("status") != "PASS"
                    or evidence.get("elf_sha256") != report["elf_sha256"]):
                report["contracts"]["status"] = "ERROR"
                raise RuntimeError("ELF contract preflight failed; see contracts and contract-preflight.log")
        with (out / "prepare.log").open("wb") as log:
            section_text = subprocess.check_output(
                [str(gdb.parent / "arm-none-eabi-objdump.exe"), "-h", str(elf)],
                timeout=15, env=dict(env, LC_ALL="C"), stderr=log, creationflags=FLAGS).decode("utf-8")
            (out / "elf-sections.txt").write_text(section_text, encoding="utf-8")
            regions = parse_sections(section_text, profile["flash_start"], profile["flash_size"])
            subprocess.run([str(gdb.parent / "arm-none-eabi-objcopy.exe"), "-O", "binary", "--gap-fill=0xFF",
                            str(elf), str(image)], check=True, timeout=15, env=env,
                           stdout=log, stderr=subprocess.STDOUT, creationflags=FLAGS)
            subprocess.run(gdb_base + ["-ex", "python import gdb, json; print(gdb.VERSION)"],
                           check=True, timeout=10, env=env, stdout=log,
                           stderr=subprocess.STDOUT, creationflags=FLAGS)
        validate_regions(regions, profile["flash_start"], profile["flash_size"], image.stat().st_size)
        report["image_verification"] = dict(scope="elf-load-sections", bin_gap_fill=255,
            gaps_verified=False, full_region_crc_verified=False, regions=regions)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        endpoint = f"127.0.0.1:{port}"
        backend = server_spec(stand, port, profile, out)
        report["backend_commands"] = dict(reset_halt=backend["reset_halt"], finish=backend["finish"],
                                          setup=backend.get("setup", []))
        run_data = dict(test=test, elf=str(elf), image=str(image), result=str(agent_result),
                        identity_policy=session.get("identity_policy", "warn"), root=str(project_root),
                        endpoint=endpoint, flash=stand["flash"], profile=profile, load_regions=regions,
                        reset_halt=backend["reset_halt"], finish=backend["finish"],
                        setup=backend.get("setup", []))
        run_file = out / "run.json"
        run_file.write_text(json.dumps(run_data), encoding="utf-8")
        env["STM32_GDBTEST_RUN"] = str(run_file)
        with (out / "server.log").open("wb") as server_log, (out / "gdb.log").open("wb") as gdb_log:
            server = subprocess.Popen(backend["command"], env=env, cwd=out,
                                      stdout=server_log, stderr=subprocess.STDOUT, creationflags=FLAGS)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if server.poll() is not None:
                    raise RuntimeError("GDB server exited before ready; see server.log")
                if backend["ready"] in (out / "server.log").read_text(errors="replace"):
                    ready = True
                    break
                time.sleep(0.1)
            if not ready:
                raise TimeoutError("GDB server startup timed out")
            client = subprocess.Popen(gdb_base + [str(elf), "-x", str(ROOT / "stm32_gdbtest/agent.py")],
                                      env=env, cwd=project_root, stdout=gdb_log, stderr=subprocess.STDOUT,
                                      creationflags=FLAGS)
            returncode = client.wait(timeout=timeout)
        if not agent_result.exists():
            raise RuntimeError(f"GDB exited {returncode} without report; see gdb.log")
        result = json.loads(agent_result.read_text(encoding="utf-8"))
        if (result.get("id") != test["id"] or result.get("elf_sha256") != report["elf_sha256"]
                or result.get("status") not in CODES or returncode != CODES[result["status"]]):
            raise RuntimeError("Invalid or inconsistent GDB report")
        report.update(result)
    except BaseException:
        report.update(status="ERROR", error=traceback.format_exc())
    finally:
        try:
            stop_tree(client)
            if (ready and report.get("connection_attempted", True)
                    and report.get("teardown") != "reset_run"):
                with (out / "recovery.log").open("wb") as log:
                    finish = [item for command in backend["finish"] for item in ("-ex", command)]
                    subprocess.run(gdb_base + ["-ex", "set confirm off", "-ex",
                                   "target extended-remote " + endpoint] + finish,
                                   check=True, timeout=10, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, creationflags=FLAGS)
                report["teardown"] = "reset_run (host recovery)"
        except BaseException:
            report.update(status="ERROR", teardown_error=traceback.format_exc())
        finally:
            try:
                stop_tree(server)
            except BaseException:
                report.update(status="ERROR", cleanup_error=traceback.format_exc())
