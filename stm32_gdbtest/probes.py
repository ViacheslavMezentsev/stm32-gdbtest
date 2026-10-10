"""Debugger probes and GDB server settings that used to be branches in the code (portability P1-3…P1-5).

Defaults reproduce the previous behaviour: OpenOCD with an ST-Link interface, J-Link over SWD with a fixed device
table for the STM32 parts the module was checked on.
"""

from pathlib import PurePosixPath
import os
import re


# J-Link device names of the MCUs the module was validated on; a profile may name its own (`jlink_device`).
JLINK_DEVICES = {"STM32F103C8T6": "STM32F103C8", "STM32F103CBT6": "STM32F103CB", "STM32F030R8T6": "STM32F030R8"}
JLINK_INTERFACES = ("SWD", "JTAG")
OPENOCD_INTERFACE = "interface/stlink.cfg"
# OpenOCD reset commands a profile may name; `reset init` runs the target's init procedure (clocks, Flash setup).
OPENOCD_RESET_HALT = ("monitor reset halt", "monitor reset init")
OPENOCD_RESET_RUN = ("monitor reset run",)
# Reset dialects of the accepted GDB servers. `monitor reset` is the one command the ST-LINK GDB Server
# documents for a reset (manual DM00613038, 2.9) and leaves the core halted; `monitor reset halt` is
# OpenOCD syntax and the ST server answers `Protocol error with Rcmd` to it.
BACKEND_RESET_HALT = {"openocd": OPENOCD_RESET_HALT, "stlink": ("monitor reset",), "jlink": ("monitor reset",)}
BACKEND_RESET_RUN = {"openocd": OPENOCD_RESET_RUN, "stlink": (), "jlink": ()}
# A schema 2 profile keeps the commands of each server in a section named after the backend.
BACKEND_SECTIONS = ("openocd", "jlink", "stlink")
OPENOCD_TRANSPORTS = ("swd", "jtag", "hla_swd", "hla_jtag", "dapdirect_swd", "dapdirect_jtag", "sdi")
_SCRIPT = re.compile(r"interface/[A-Za-z0-9_.-]+\.cfg")
_DEVICE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")


def validate_stand(data):
    """Optional probe keys of a stand: `interface` and `transport` (OpenOCD), `interface` (J-Link)."""
    backend = data.get("backend")
    if backend == "openocd":
        if "interface" in data and not (isinstance(data["interface"], str) and _SCRIPT.fullmatch(data["interface"])):
            raise ValueError("interface must be an OpenOCD script such as interface/stlink.cfg")
        if "transport" in data and data["transport"] not in OPENOCD_TRANSPORTS:
            raise ValueError("transport must be one of " + ", ".join(OPENOCD_TRANSPORTS))
    elif backend == "jlink":
        if "interface" in data and data["interface"] not in JLINK_INTERFACES:
            raise ValueError("J-Link interface must be SWD or JTAG")
    return data


def family(stand):
    """Probe family for ownership locks: ST-Link for the ST server and the default OpenOCD interface."""
    if stand["backend"] == "jlink":
        return "jlink"
    if stand["backend"] == "stlink":
        return "stlink"
    name = PurePosixPath(stand.get("interface", OPENOCD_INTERFACE)).stem.lower()
    return "stlink" if name.startswith("stlink") else re.sub(r"[^a-z0-9_-]", "-", name)


def jlink_device(profile):
    """J-Link device name: the profile key `jlink_device`, else the validated table."""
    device = profile.get("jlink_device") or JLINK_DEVICES.get(profile["mcu"])
    if not device:
        raise ValueError("J-Link device mapping not validated for this MCU")
    return device


def validate_profile_keys(data):
    """Optional server keys of a schema 1 profile."""
    device = data.get("jlink_device")
    if "jlink_device" in data and not (isinstance(device, str) and _DEVICE.fullmatch(device)):
        raise ValueError("Invalid J-Link device name")


def validate_profile_sections(data):
    """Backend sections of a schema 2 profile: a section per server, keys named after the actions.

    A section is optional; an absent section or an absent key means the built-in dialect of that backend.
    `reset_run` belongs to OpenOCD only, because the ST and J-Link dialects finish the session with their
    own commands.
    """
    sections = {name: data[name] for name in BACKEND_SECTIONS if name in data}
    for name, section in sections.items():
        if not isinstance(section, dict):
            raise ValueError(f"Section {name} must be a table")
        extra = set(section) - {"reset_halt", "reset_run"}
        if extra:
            raise ValueError(f"Unknown key in section {name}: {sorted(extra)[0]}")
        if "reset_run" in section and name != "openocd":
            raise ValueError(f"Section {name} does not use reset_run")
        if "reset_halt" in section and section["reset_halt"] not in BACKEND_RESET_HALT[name]:
            raise ValueError(f"Invalid {name} reset_halt: {section['reset_halt']!r}")
        if "reset_run" in section and section["reset_run"] not in BACKEND_RESET_RUN[name]:
            raise ValueError(f"Invalid {name} reset_run: {section['reset_run']!r}")


def dialect(profile, backend):
    """Reset commands of one backend: the session override wins, then the profile section, then the dialect.

    ТЗ API 6.6: the run resolves the command once, so `Target.reset()` and the boot sequence use the same
    value; the environment variable is the session override of the documented precedence.
    """
    if backend not in BACKEND_RESET_HALT:
        raise ValueError("Unsupported backend")
    override = os.environ.get("STM32_GDBTEST_RESET_COMMAND")
    if override is not None and (not override.strip() or any(c in override for c in "\r\n\0")):
        raise ValueError("STM32_GDBTEST_RESET_COMMAND must be a non-empty single-line command")
    section = profile.get(backend)
    if section is not None and not isinstance(section, dict):
        raise ValueError(f"Section {backend} must be a table")
    section = section or {}
    if profile.get("schema") == 1 and backend == "openocd":
        section = {key: profile[key] for key in ("reset_halt", "reset_run") if key in profile}
    halt = override or section.get("reset_halt") or BACKEND_RESET_HALT[backend][0]
    run = [section["reset_run"]] if "reset_run" in section else list(BACKEND_RESET_RUN[backend])
    return halt, run
