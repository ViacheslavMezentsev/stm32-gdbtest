"""Server dialects: shared test scenarios never contain vendor monitor commands."""

import os
from pathlib import Path
import re
import shutil
import tomllib

from stm32_gdbtest import openocd, probes, remote as remote_host
from stm32_gdbtest.toolchain import expand_path


# Vendor names differ by OS: SEGGER ships JLinkGDBServerCLExe on Linux; ST keeps the
# names and drops .exe. ST-LINK GDB Server has no Linux arm64 build.
WINDOWS = os.name == "nt"
DEFAULT_SERVER = {
    "jlink": "JLinkGDBServerCL.exe" if WINDOWS else "JLinkGDBServerCLExe",
    "stlink": "ST-LINK_gdbserver.exe" if WINDOWS else "ST-LINK_gdbserver",
}
PROGRAMMER = "STM32_Programmer_CLI.exe" if WINDOWS else "STM32_Programmer_CLI"


def load_stand(path):
    document = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    data = document["probe"]
    # ТЗ 5.18.1: [remote] moves the server to a stand host; its tools are resolved there.
    remote = remote_host.load(document.get("remote"))
    local = remote is None
    if data.get("backend") == "openocd":
        return dict(openocd.validate(data, local), remote=remote)
    if data.get("backend") not in ("stlink", "jlink"):
        raise ValueError("Supported backends: openocd, stlink, jlink")
    allowed = {"backend", "serial", "executable", "speed_khz", "flash", "startup_timeout_s"}
    if data["backend"] == "stlink":
        allowed.add("programmer_dir")
    if data["backend"] == "jlink":
        allowed.add("interface")
    if set(data) - allowed:
        raise ValueError("Unknown probe setting; check the stand TOML")
    probes.validate_stand(data)
    if not re.fullmatch(r"[A-Za-z0-9]+", data.get("serial", "")):
        raise ValueError("Set an alphanumeric debugger serial in the local stand file")
    if data["backend"] == "jlink" and not re.fullmatch(r"[1-9][0-9]{3,}", data["serial"]):
        raise ValueError("J-Link requires an explicit decimal USB serial, not an index or nickname")
    speed = data.get("speed_khz", 1000)
    if type(speed) is not int or not 1 <= speed <= 4000:
        raise ValueError("speed_khz must be an integer between 1 and 4000")
    policy = data.get("flash", "if-different")
    if policy not in ("if-different", "verify-only"):
        raise ValueError("flash must be if-different or verify-only")
    data = dict(data, startup_timeout_s=openocd.startup_timeout(data))
    if local:
        executable = shutil.which(expand_path(data.get("executable", DEFAULT_SERVER[data["backend"]])))
    else:
        executable = data.get("executable", remote_host.stand_executable_default(data["backend"]))
    if not executable:
        raise FileNotFoundError("GDB Server executable not found")
    if data["backend"] == "jlink":
        return dict(data, executable=executable, speed_khz=speed, flash=policy, remote=remote)
    if local:
        programmer = Path(expand_path(data.get("programmer_dir", "")))
        if not programmer.is_absolute() or not (programmer / PROGRAMMER).is_file():
            raise ValueError("programmer_dir must contain " + PROGRAMMER)
        programmer = str(programmer)
    else:
        programmer = data.get("programmer_dir", "")
        if not isinstance(programmer, str) or not programmer.startswith("/"):
            raise ValueError("programmer_dir must be an absolute path on the stand host")
    return dict(data, executable=executable, programmer_dir=programmer,
                speed_khz=speed, flash=policy, remote=remote)


def server_spec(stand, port, profile, out):
    # ТЗ 6.4.2/6.5.3: the reset commands come from the dialect of the backend, overridden by the
    # profile section of that backend (schema 2) or by the profile keys (schema 1).
    reset_halt, reset_run = probes.dialect(profile, stand["backend"])
    if stand["backend"] == "jlink":
        return dict(
            command=[stand["executable"], "-device", probes.jlink_device(profile),
                     "-if", stand.get("interface", "SWD"), "-speed", str(stand["speed_khz"]),
                     "-USB", stand["serial"], "-port", str(port),
                     "-swoport", "0", "-telnetport", "0", "-RTTTelnetPort", "0",
                     "-localhostonly", "1", "-nogui", "-strict", "-timeout", "5000",
                     "-noir", "-noreset", "-nohalt", "-nosinglerun", "-vd",
                     "-log", str(out / "jlink.log")],
            ready="Waiting for GDB connection",
            setup=["monitor flash breakpoints = 0"],
            reset_halt=reset_halt,
            finish=[reset_halt, "monitor go", "disconnect"],
        )
    if stand["backend"] == "openocd":
        return dict(command=openocd.server_command(stand, port, profile),
                    ready=f"Listening on port {port} for gdb connections",
                    reset_halt=reset_halt,
                    finish=[*reset_run, "disconnect"])
    if stand["backend"] != "stlink":
        raise ValueError("Unsupported backend")
    return dict(
        command=[stand["executable"], "-d", "-e", "-g", "-p", str(port),
                 "-i", stand["serial"], "--frequency", str(stand["speed_khz"]),
                 "-cp", stand["programmer_dir"], "--temp-path", str(out),
                 "-f", str(out / "stlink.log"), "-l", "31", "-s"],
        ready="Waiting for debugger connection",
        reset_halt=reset_halt,
        finish=[reset_halt, "detach"],
    )
