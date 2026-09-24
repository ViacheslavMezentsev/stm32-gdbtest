"""Runtime evidence only: never infer build libraries from a current workspace."""

import platform
import re


REQUIRED_GDB_API = (
    "execute", "parse_and_eval", "selected_inferior", "newest_frame",
    "Breakpoint", "Breakpoint.pending", "Breakpoint.condition",
    "Breakpoint.is_valid", "Breakpoint.delete", "BP_HARDWARE_BREAKPOINT",
    "Value.is_optimized_out", "Value.fetch_lazy", "Frame.name", "Frame.read_register",
    "Inferior.read_memory", "events.stop.connect", "events.stop.disconnect",
)


def inspect_gdb_api(api):
    """Presence checks, not proof of semantics; called on the GDB main thread."""
    checks = {}
    for name in REQUIRED_GDB_API:
        value = api
        for component in name.split("."):
            value = getattr(value, component, None)
            if value is None:
                break
        checks[name] = value is not None
    return checks


def require_gdb_api(checks):
    missing = [name for name in REQUIRED_GDB_API if checks.get(name) is not True]
    if missing:
        raise RuntimeError("Required GDB Python API unavailable: " + ", ".join(missing))


def runtime_manifest(report, server_log=""):
    """Extract allowlisted tokens, never copy log lines containing stand identity."""
    name = report.get("backend", "openocd")
    if name == "jlink":
        backend = re.search(r"SEGGER J-Link GDB Server V([0-9][A-Za-z0-9._-]*)", server_log)
        debugger = re.search(r"^Firmware: (J-Link [A-Za-z0-9 -]+ compiled [A-Za-z]{3}\s+\d{1,2} \d{4} \d{2}:\d{2}:\d{2})\s*$", server_log, re.M)
        api = None
    elif name == "stlink":
        backend = re.search(r"ST-LINK GDB server\. Version ([0-9][A-Za-z0-9.+_-]*)", server_log)
        debugger = re.search(r"ST-LINK Firmware version\s*:\s*(V[0-9]+J[0-9]+(?:[A-Z][0-9]+)*)", server_log)
        api = None  # This server does not publish the OpenOCD STLINK API field.
    else:
        backend = re.search(r"^Open On-Chip Debugger ([0-9][A-Za-z0-9.+_-]*)\b", server_log, re.M)
        debugger = re.search(r"\bSTLINK (V[0-9]+J[0-9]+(?:[A-Z][0-9]+)*) \(API v([0-9]+)\)", server_log)
        api = int(debugger.group(2)) if debugger else None
    return {
        "schema": 1,
        "scope": "runtime-only",
        "host": {"python": platform.python_version(), "system": platform.system()},
        "gdb": {
            "version": report.get("gdb_version"),
            "python": report.get("python_version"),
            "required_api_presence": report.get("gdb_api_checks"),
            "evidence": "agent" if "gdb_version" in report else "unavailable: no agent report",
        },
        "backend": {
            "name": name,
            "version": backend.group(1) if backend else None,
            "evidence": "server.log banner" if backend else "unavailable: banner not recognized",
        },
        "debugger": {
            "firmware": debugger.group(1) if debugger else None,
            "api": api,
            "evidence": ("server.log firmware banner" if name == "jlink" else "server.log STLINK banner")
                        if debugger else "unavailable: banner not recognized",
        },
        "build": {
            "elf_sha256": report.get("elf_sha256"),
            "image_sha256": report.get("bin_sha256"),
            "provenance": "verified: report.build_manifest" if "build_manifest" in report
                          else "unavailable: no verified build manifest",
        },
    }
