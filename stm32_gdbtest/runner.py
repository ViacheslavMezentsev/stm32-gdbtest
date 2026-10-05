"""Host orchestrator: snapshot, probe ownership, lifecycle and reports."""

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import random
import socket
import subprocess
import time
import traceback

from stm32_gdbtest.backends import load_stand, server_spec
from stm32_gdbtest.configuration import capture, thaw
from stm32_gdbtest.config_transport import dumps
from stm32_gdbtest.processes import FLAGS, probe_identity, probe_lock, spawn_options, stop_tree
from stm32_gdbtest import remote as remote_host
from stm32_gdbtest.reports import CODES, write_reports
from stm32_gdbtest.compatibility import runtime_manifest
from stm32_gdbtest.build_manifest import load_verified
from stm32_gdbtest.contracts import select_contracts, select_contracts_from
from stm32_gdbtest.image import parse_sections, validate_regions
from stm32_gdbtest.full_image import load_policy, canonical_image


ROOT = Path(__file__).resolve().parents[1]


def local_directory(path, root=ROOT):
    path = Path(path).resolve()
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError("Output directories must remain inside the selected project root")
    path.mkdir(parents=True, exist_ok=True)
    return path


def tool(gdb, name):
    """GNU binutils next to the selected GDB; Windows installations carry an .exe suffix."""
    gdb = Path(gdb)
    return str(gdb.parent / (name + (gdb.suffix if gdb.suffix.lower() == ".exe" else "")))


def run(session, test, stand_path=None, timeout=None, identity_policy=None, image_policy=None,
        prepare_only=False):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    project_root = Path(session.get("root", ROOT)).resolve()
    out = local_directory(Path(session["out"]) / f"{stamp}-{test['id']}-{os.getpid()}", project_root)
    started = time.monotonic()
    report = {"id": test["id"], "status": "ERROR", "checks": [], "started_utc": stamp,
              "mode": "prepare" if prepare_only else "hardware"}
    if session.get("package"):
        report["package"] = session["package"]  # ТЗ 5.19.3: provenance of a prepared run
    try:
        legacy = [name for name in ("HWTEST_STAND", "HWTEST_IDENTITY_POLICY") if os.environ.get(name)]
        if legacy:
            raise ValueError("Rename legacy environment variables to STM32_GDBTEST_: " + ", ".join(legacy))
        policy = identity_policy or os.environ.get("STM32_GDBTEST_IDENTITY_POLICY", "warn")
        if policy not in ("warn", "strict"):
            raise ValueError("Identity policy must be warn or strict")
        session = dict(session, identity_policy=policy,
                       image_policy_path=image_policy or os.environ.get("STM32_GDBTEST_IMAGE_POLICY"))
        report["identity_policy"] = policy
        limit = test["timeout_s"] if timeout is None else timeout
        if not math.isfinite(limit) or not 0 < limit <= 300:
            raise ValueError("Timeout must be positive and <= 300 seconds")
        path = stand_path or os.environ.get("STM32_GDBTEST_STAND") or session.get("stand")
        if not path and not prepare_only:
            raise RuntimeError("Select a local stand with STM32_GDBTEST_STAND or --stand")
        # ТЗ 5.16.2: preparation validates a stand only when one is selected.
        stand = load_stand(path) if path else None
        if stand:
            report["backend"] = stand["backend"]
            if stand.get("remote"):
                report["server_host"] = stand["remote"]["host"]
        configuration = capture(session, image_policy=image_policy)
        session = dict(session, _configuration=configuration)
        profile = thaw(configuration.config['target'])
        report["profile"] = profile
        if prepare_only:
            # ТЗ 5.16.1: no debugger ownership, server or GDB connection in preparation.
            execute(session, test, stand, out, report, limit, profile, prepare_only=True)
        else:
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


def execute(session, test, stand, out, report, timeout, profile, prepare_only=False):
    server = client = remote = heartbeat = None
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
        full_policy = None
        program_elf = None
        program_sha = None
        configuration = session.get('_configuration')
        if configuration:
            (out / 'config.json').write_text(dumps(configuration), encoding='utf-8')
        if configuration and configuration.config['image'] is not None:
            full_policy = thaw(configuration.config['image']['image'])
            policy_sha = configuration.config_props['image']['sha256']
            report['image_policy'] = dict(full_policy, source_sha256=policy_sha)
            (out / 'image-policy.json').write_text(json.dumps(report['image_policy'], indent=2), encoding='utf-8')
        elif not configuration and session.get("image_policy_path"):
            full_policy, policy_sha = load_policy(session["image_policy_path"], profile)
            report["image_policy"] = dict(full_policy, source_sha256=policy_sha)
            (out / "image-policy.json").write_text(json.dumps(report["image_policy"], indent=2), encoding="utf-8")
        # All clients consume this immutable per-run snapshot, never a changing build ELF.
        elf.write_bytes(Path(session["elf"]).read_bytes())
        report["elf_sha256"] = hashlib.sha256(elf.read_bytes()).hexdigest()
        if session.get("build_manifest"):
            manifest = load_verified(session["build_manifest"], report["elf_sha256"], session["profile"],
                profile_sha256=configuration.config_props['target']['sha256'] if configuration else None)
            report["build_manifest"] = manifest
            (out / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        names = test.get("contracts", [])
        report["contracts"] = dict(schema=1, requested=names, status="ERROR" if names else "NOT_REQUESTED")
        # ТЗ 3.5: the registry sits in tests/ next to the scenarios, not next to target.toml. With extra
        # scenario directories the profile's registry is searched first, then the scenario's own one, then
        # the remaining directories, so a device-specific contract overrides a general one (ТЗ API 5.8).
        tests_root = Path(session["tests"]).parent if session.get("tests") else Path(session["profile"]).parent / "Tests"
        roots = [tests_root]
        if test.get("path"):
            roots.append(Path(test["path"]).parent.parent)
        roots += [Path(item).parent for item in session.get("test_dirs", [])]
        registries = list(dict.fromkeys((root / "contracts.json").resolve() for root in roots))
        selected = select_contracts_from(registries, names, report.get("build_manifest"))
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
                [tool(gdb, "arm-none-eabi-objdump"), "-h", str(elf)],
                timeout=15, env=dict(env, LC_ALL="C"), stderr=log, creationflags=FLAGS).decode("utf-8")
            (out / "elf-sections.txt").write_text(section_text, encoding="utf-8")
            regions = parse_sections(section_text, profile["flash_start"], profile["flash_size"])
            # ТЗ 4.1.5: only the selected load sections form the BIN; an empty section with an
            # LMA outside Flash (e.g. empty .data in RAM) must not stretch it to hundreds of MiB.
            selection = [item for region in regions for item in ("-j", region["name"])]
            subprocess.run([tool(gdb, "arm-none-eabi-objcopy"), "-O", "binary", "--gap-fill=0xFF", *selection,
                            str(elf), str(image)], check=True, timeout=15, env=env,
                           stdout=log, stderr=subprocess.STDOUT, creationflags=FLAGS)
            subprocess.run(gdb_base + ["-ex", "python import gdb, json; print(gdb.VERSION)"],
                           check=True, timeout=10, env=env, stdout=log,
                           stderr=subprocess.STDOUT, creationflags=FLAGS)
        validate_regions(regions, profile["flash_start"], profile["flash_size"], image.stat().st_size)
        report["image_verification"] = dict(scope="elf-load-sections", bin_gap_fill=255,
            gaps_verified=False, full_region_crc_verified=False, regions=regions)
        if full_policy:
            image.write_bytes(canonical_image(image.read_bytes(), regions, full_policy, profile))
            program_elf = out / "program.elf"
            objcopy = tool(gdb, "arm-none-eabi-objcopy")
            with (out / "prepare.log").open("ab") as log:
                subprocess.run([objcopy, "-I", "binary", "-O", "elf32-littlearm", "-B", "arm",
                    "--rename-section", ".data=.firmware,alloc,load,readonly,data,contents",
                    "--change-section-address", f".data=0x{full_policy['start']:x}",
                    str(image), str(program_elf)], check=True, timeout=15, env=env,
                    stdout=log, stderr=subprocess.STDOUT, creationflags=FLAGS)
                carrier_text = subprocess.check_output(
                    [tool(gdb, "arm-none-eabi-objdump"), "-h", str(program_elf)],
                    timeout=15, env=dict(env, LC_ALL="C"), stderr=log, creationflags=FLAGS).decode("utf-8")
                (out / "program-sections.txt").write_text(carrier_text, encoding="utf-8")
                carrier = parse_sections(carrier_text, profile["flash_start"], profile["flash_size"])
                if len(carrier) != 1 or carrier[0]["size"] != image.stat().st_size:
                    raise ValueError("Programming ELF does not contain the complete BIN")
                roundtrip = out / "program-roundtrip.bin"
                subprocess.run([objcopy, "-O", "binary", str(program_elf), str(roundtrip)],
                    check=True, timeout=15, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=FLAGS)
                if roundtrip.read_bytes() != image.read_bytes():
                    raise ValueError("Programming ELF payload differs from BIN")
            program_sha = hashlib.sha256(program_elf.read_bytes()).hexdigest()
            report["program_elf_sha256"] = program_sha
            report["image_verification"] = dict(scope="full-image", policy=full_policy,
                gaps_verified=False, full_region_crc_verified=False)
        report["bin_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
        if prepare_only:
            # ТЗ 5.16.3: every host-side check has passed; the debugger is never touched.
            if stand:
                backend = server_spec(stand, 0, profile, out)
                report["backend_commands"] = dict(reset_halt=backend["reset_halt"], finish=backend["finish"],
                                                  setup=backend.get("setup", []))
            report.update(status="PASS", connection_attempted=False, hardware_accessed=False,
                          artifacts=sorted(item.name for item in out.iterdir()))
            return
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        endpoint = f"127.0.0.1:{port}"
        remote = stand.get("remote")
        if remote:
            # ТЗ 5.18.2: the helper substitutes the stand host's port and run directory.
            remote_port = random.randint(40000, 59999)
            backend = server_spec(stand, "{port}", profile, PurePosixPath("{dir}"))
            backend["ready"] = backend["ready"].replace("{port}", str(remote_port))
        else:
            backend = server_spec(stand, port, profile, out)
        report["backend_commands"] = dict(reset_halt=backend["reset_halt"], finish=backend["finish"],
                                          setup=backend.get("setup", []))
        run_data = dict(test=test, elf=str(elf), image=str(image), result=str(agent_result),
                        configuration=dumps(configuration) if configuration else None,
                        identity_policy=session.get("identity_policy", "warn"), root=str(project_root),
                        endpoint=endpoint, flash=stand["flash"], profile=profile, load_regions=regions,
                        full_image_policy=full_policy, program_elf=str(program_elf) if program_elf else None,
                        program_elf_sha256=program_sha, expected_bin_sha256=report["bin_sha256"],
                        reset_halt=backend["reset_halt"], finish=backend["finish"],
                        setup=backend.get("setup", []),
                        # ТЗ API 4.14.2: the stand as the scenario sees it, without serials or addresses.
                        stand_info=dict(backend=stand["backend"], server="remote" if remote else "local",
                                        speed_khz=stand.get("speed_khz"), flash=stand["flash"]))
        run_file = out / "run.json"
        run_file.write_text(json.dumps(run_data), encoding="utf-8")
        env["STM32_GDBTEST_RUN"] = str(run_file)
        with (out / "server.log").open("wb") as server_log, (out / "gdb.log").open("wb") as gdb_log, \
                (out / "tunnel.log").open("wb") if remote else open(os.devnull, "wb") as tunnel_log:
            limit = stand.get("startup_timeout_s", 10)
            if remote:
                config = remote_host.serve_config(probe_identity(stand["serial"], stand["backend"]),
                                                  remote_port, backend["command"])
                command = remote_host.ssh_command(remote, "-v", "-o", "ExitOnForwardFailure=yes", "-L",
                                                  f"127.0.0.1:{port}:127.0.0.1:{remote_port}")
                server = subprocess.Popen(command + [remote_host.remote_script(remote, config)], env=env,
                                          cwd=out, stdin=subprocess.PIPE, stdout=server_log, stderr=tunnel_log,
                                          **spawn_options())
                heartbeat = remote_host.Heartbeat(server.stdin)
                limit += 10  # SSH connection and authentication
            else:
                server = subprocess.Popen(backend["command"], env=env, cwd=out,
                                          stdout=server_log, stderr=subprocess.STDOUT, **spawn_options())
            deadline = time.monotonic() + limit
            while time.monotonic() < deadline:
                text = (out / "server.log").read_text(errors="replace")
                if remote and remote_host.parse_marker(text, "error"):
                    raise RuntimeError("Stand host refused the run: " + remote_host.parse_marker(text, "error"))
                if server.poll() is not None:
                    hint = remote_host.environment_hint(server.returncode) if remote else ""
                    raise RuntimeError("GDB server exited before ready; see server.log"
                                       + (" and tunnel.log" + (f" ({hint})" if hint else "") if remote else ""))
                if backend["ready"] in text and (not remote or remote_host.forwarding_ready(
                        (out / "tunnel.log").read_text(errors="replace"))):
                    ready = True
                    break
                time.sleep(0.1)
            if not ready:
                raise TimeoutError(f"GDB server startup timed out after {limit} s; see server.log "
                                   "(a slow probe connection may need startup_timeout_s in the stand)")
            client = subprocess.Popen(gdb_base + [str(elf), "-x", str(ROOT / "stm32_gdbtest/agent.py")],
                                      env=env, cwd=project_root, stdout=gdb_log, stderr=subprocess.STDOUT,
                                      **spawn_options())
            returncode = client.wait(timeout=timeout)
        if not agent_result.exists():
            raise RuntimeError(f"GDB exited {returncode} without report; see gdb.log")
        result = json.loads(agent_result.read_text(encoding="utf-8"))
        if (result.get("id") != test["id"] or result.get("elf_sha256") != report["elf_sha256"]
                or result.get("bin_sha256") != report["bin_sha256"]
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
                if heartbeat is not None:
                    heartbeat.stop()
                if remote and server is not None and server.poll() is None:
                    # EOF on the session lets the helper stop the server, send its logs and unlock.
                    server.stdin.close()
                    try:
                        server.wait(timeout=12)
                    except subprocess.TimeoutExpired:
                        pass
                stop_tree(server)
            except BaseException:
                report.update(status="ERROR", cleanup_error=traceback.format_exc())
