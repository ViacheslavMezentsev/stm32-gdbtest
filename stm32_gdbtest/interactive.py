"""Interactive run of one scenario for its author (ТЗ API 6.10).

`run --interactive` is chosen by the person who starts the run, never by the scenario: the same
scenario keeps its `timeout_s` and runs unchanged in CTest and CI. An interactive run

- waits for a Python debugger (debugpy, 127.0.0.1) inside GDB before the MCU is touched;
- has no wall-clock limit for the GDB agent and no scenario deadline for async scenarios,
  so a person may stay at a breakpoint as long as needed; Ctrl+C cancels the run;
- keeps server startup, preparation, per-operation and recovery limits;
- writes its results to a sibling `interactive-runs` directory with `execution_kind: interactive`,
  so automated readers of `runs/*/result.json` never see it.
"""
import glob
import json
import os
from pathlib import Path
import re
import socket
import sys

KIND = "interactive"
ROOT_NAME = "interactive-runs"
DEFAULT_PORT = 5678
READY_FILE = "debugger-ready.json"
EXTENSION_ROOTS = (".vscode", ".vscode-server", ".vscode-insiders")


def results_root(out):
    """Interactive results live next to the automated `runs` directory, never inside it."""
    return Path(out).parent / ROOT_NAME


def _version_key(path):
    match = re.search(r"debugpy-([0-9][0-9.]*)", str(path))
    return tuple(int(part) for part in match.group(1).strip(".").split(".")) if match else ()


def debugpy_directory(explicit=None, home=None):
    """Directory that contains the `debugpy` package: argument, STM32_GDBTEST_DEBUGPY or the VS Code extension."""
    if explicit or os.environ.get("STM32_GDBTEST_DEBUGPY"):
        candidates = [Path(explicit or os.environ["STM32_GDBTEST_DEBUGPY"])]
    else:
        home = Path(home or Path.home())
        found = []
        for root in EXTENSION_ROOTS:
            found += glob.glob(str(home / root / "extensions" / "ms-python.debugpy-*" / "bundled" / "libs"))
        candidates = [Path(item) for item in sorted(found, key=_version_key, reverse=True)]
    for candidate in candidates:
        if (candidate / "debugpy" / "__init__.py").is_file():
            return candidate.resolve()
    raise RuntimeError("debugpy not found: install the VS Code extension ms-python.debugpy, "
                       "set STM32_GDBTEST_DEBUGPY or pass --debugpy <directory with the debugpy package>")


def check_port(port):
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Debugger port must be an integer 1..65535")
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as error:
            raise RuntimeError(f"Debugger port 127.0.0.1:{port} is busy: {error}") from None


def settings(port=DEFAULT_PORT, debugpy=None):
    """Validated settings passed from the runner to the GDB agent; resolved before any hardware access."""
    check_port(port)
    return {"port": port, "debugpy": str(debugpy_directory(debugpy))}


def attach(config, ready_path):
    """Inside GDB: listen on loopback, announce readiness and wait for the debugger before the MCU is touched."""
    sys.path.insert(0, config["debugpy"])
    import debugpy
    debugpy.listen(("127.0.0.1", config["port"]), in_process_debug_adapter=True)
    Path(ready_path).write_text(json.dumps({"port": config["port"], "debugpy": getattr(debugpy, "__version__", None)}),
                                encoding="utf-8")
    debugpy.wait_for_client()
