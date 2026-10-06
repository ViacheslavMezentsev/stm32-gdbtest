"""Debugger probes and GDB server settings that used to be branches in the code (portability P1-3…P1-5).

Defaults reproduce the previous behaviour: OpenOCD with an ST-Link interface, J-Link over SWD with a fixed device
table for the STM32 parts the module was checked on.
"""

from pathlib import PurePosixPath
import re


# J-Link device names of the MCUs the module was validated on; a profile may name its own (`jlink_device`).
JLINK_DEVICES = {"STM32F103C8T6": "STM32F103C8", "STM32F103CBT6": "STM32F103CB", "STM32F030R8T6": "STM32F030R8"}
JLINK_INTERFACES = ("SWD", "JTAG")
OPENOCD_INTERFACE = "interface/stlink.cfg"
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
