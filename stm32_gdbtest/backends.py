"""Server dialects: shared test scenarios never contain vendor monitor commands."""

from pathlib import Path
import re
import shutil
import tomllib

from stm32_gdbtest import openocd


def load_stand(path):
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))["probe"]
    if data.get("backend") == "openocd":
        return openocd.load_stand(path)
    if data.get("backend") not in ("stlink", "jlink"):
        raise ValueError("Supported backends: openocd, stlink, jlink")
    allowed = {"backend", "serial", "executable", "speed_khz", "flash"}
    if data["backend"] == "stlink":
        allowed.add("programmer_dir")
    if set(data) - allowed:
        raise ValueError("Unknown probe setting; check the stand TOML")
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
    default = "JLinkGDBServerCL.exe" if data["backend"] == "jlink" else "ST-LINK_gdbserver.exe"
    executable = shutil.which(data.get("executable", default))
    if not executable:
        raise FileNotFoundError("GDB Server executable not found")
    if data["backend"] == "jlink":
        return dict(data, executable=executable, speed_khz=speed, flash=policy)
    programmer = Path(data.get("programmer_dir", ""))
    if not programmer.is_absolute() or not (programmer / "STM32_Programmer_CLI.exe").is_file():
        raise ValueError("programmer_dir must contain STM32_Programmer_CLI.exe")
    return dict(data, executable=executable, programmer_dir=str(programmer),
                speed_khz=speed, flash=policy)


def server_spec(stand, port, profile, out):
    if stand["backend"] == "jlink":
        devices = {"STM32F103C8T6": "STM32F103C8", "STM32F030R8T6": "STM32F030R8"}
        if profile["mcu"] not in devices:
            raise ValueError("J-Link device mapping not validated for this MCU")
        return dict(
            command=[stand["executable"], "-device", devices[profile["mcu"]],
                     "-if", "SWD", "-speed", str(stand["speed_khz"]),
                     "-USB", stand["serial"], "-port", str(port),
                     "-swoport", "0", "-telnetport", "0", "-RTTTelnetPort", "0",
                     "-localhostonly", "1", "-nogui", "-strict", "-timeout", "5000",
                     "-noir", "-noreset", "-nohalt", "-nosinglerun", "-vd",
                     "-log", str(out / "jlink.log")],
            ready="Waiting for GDB connection",
            setup=["monitor flash breakpoints = 0"],
            reset_halt="monitor reset",
            finish=["monitor reset", "monitor go", "disconnect"],
        )
    if stand["backend"] == "openocd":
        return dict(command=openocd.server_command(stand, port, profile),
                    ready=f"Listening on port {port} for gdb connections",
                    reset_halt=profile["reset_halt"],
                    finish=[profile["reset_run"], "disconnect"])
    if stand["backend"] != "stlink":
        raise ValueError("Unsupported backend")
    return dict(
        command=[stand["executable"], "-d", "-e", "-g", "-p", str(port),
                 "-i", stand["serial"], "--frequency", str(stand["speed_khz"]),
                 "-cp", stand["programmer_dir"], "--temp-path", str(out),
                 "-f", str(out / "stlink.log"), "-l", "31", "-s"],
        ready="Waiting for debugger connection",
        reset_halt="monitor reset",
        finish=["monitor reset", "detach"],
    )
