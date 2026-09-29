"""OpenOCD command dialect, independent of firmware tests."""

from pathlib import Path
import re
import shutil
import tomllib

from stm32_gdbtest.toolchain import expand_path


DEFAULT_STARTUP_TIMEOUT_S = 10


def startup_timeout(data):
    """ТЗ 3.4.10: wait for the server ready marker; some probes connect slowly."""
    value = data.get("startup_timeout_s", DEFAULT_STARTUP_TIMEOUT_S)
    if type(value) is not int or not 1 <= value <= 120:
        raise ValueError("startup_timeout_s must be an integer between 1 and 120")
    return value


def load_stand(path):
    return validate(tomllib.loads(Path(path).read_text(encoding="utf-8"))["probe"])


def validate(data, local=True):
    """[probe] for OpenOCD; a remote stand resolves the executable on the stand host."""
    if set(data) - {"backend", "serial", "executable", "speed_khz", "flash", "startup_timeout_s"}:
        raise ValueError("Unknown probe setting; check the stand TOML")
    if data.get("backend") != "openocd":
        raise ValueError("Only the openocd backend is supported")
    if not re.fullmatch(r"[A-Za-z0-9]+", data.get("serial", "")):
        raise ValueError("Set an alphanumeric ST-Link serial in the local stand file")
    speed = data.get("speed_khz", 1000)
    if type(speed) is not int or not 1 <= speed <= 4000:
        raise ValueError("speed_khz must be an integer between 1 and 4000")
    policy = data.get("flash", "if-different")
    if policy not in ("if-different", "verify-only"):
        raise ValueError("flash must be if-different or verify-only")
    executable = (shutil.which(expand_path(data.get("executable", "openocd"))) if local
                  else data.get("executable", "openocd"))
    if not executable:
        raise FileNotFoundError("OpenOCD executable not found")
    return dict(data, executable=executable, speed_khz=speed, flash=policy,
                startup_timeout_s=startup_timeout(data))


def server_command(stand, port, profile):
    return [stand["executable"], "-f", "interface/stlink.cfg", "-f", profile["openocd_target"],
            "-c", f"adapter serial {stand['serial']}", "-c", f"adapter speed {stand['speed_khz']}",
            "-c", "bindto 127.0.0.1", "-c", f"gdb_port {port}",
            "-c", "tcl_port disabled", "-c", "telnet_port disabled"]
