"""Validated target description; no implicit fallback to a different MCU."""

from pathlib import Path
import re
import tomllib

from stm32_gdbtest.probes import (BACKEND_SECTIONS, OPENOCD_RESET_HALT, OPENOCD_RESET_RUN,
                                  validate_profile_keys, validate_profile_sections)


def load_profile(path):
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    return validate_profile(data)


def validate_profile(data):
    """Validate a parsed snapshot without reading its original source again.

    Schema 1 keeps the OpenOCD reset commands at the top level; schema 2 moves them into a section per
    GDB server (`[openocd]`, `[jlink]`, `[stlink]`, `[st-util]`), so one profile serves every backend.
    """
    required = {"schema", "name", "mcu", "openocd_target", "flash_start", "flash_size",
                "breakpoint_limit", "fault_handlers", "core_registers", "identity",
                "diagnostic_registers"}
    optional = {"flash_size_address", "jlink_device"}
    schema = data.get("schema")
    if type(schema) is not int or schema not in (1, 2):
        raise ValueError("Invalid target profile schema or keys")
    if schema == 1:
        required = required | {"reset_halt", "reset_run"}
    else:
        # The reset commands belong to the backend sections; the old top-level keys are refused so that a
        # profile cannot name a command for a server it does not speak.
        optional = optional | set(BACKEND_SECTIONS)
    if not required <= set(data) or set(data) - required - optional:
        raise ValueError("Invalid target profile schema or keys")
    for key in ("name", "mcu"):
        if not isinstance(data[key], str) or not re.fullmatch(r"[A-Za-z0-9]+", data[key]):
            raise ValueError(f"Invalid profile {key}")
    if not re.fullmatch(r"target/[A-Za-z0-9_-]+\.cfg", data["openocd_target"]):
        raise ValueError("Invalid OpenOCD target script")
    for key in ("flash_start", "flash_size", "breakpoint_limit"):
        if type(data[key]) is not int or not 0 < data[key] <= 0xFFFFFFFF:
            raise ValueError(f"Invalid profile {key}")
    if data["flash_start"] + data["flash_size"] > 0x100000000:
        raise ValueError("Flash range overflow")
    for key in ("fault_handlers", "core_registers"):
        values = data[key]
        if not isinstance(values, list) or any(not isinstance(v, str) or not re.fullmatch(
                r"[A-Za-z_][A-Za-z0-9_]*", v) for v in values) or len(set(values)) != len(values):
            raise ValueError(f"Invalid profile {key}")
    if data["breakpoint_limit"] <= len(data["fault_handlers"]):
        raise ValueError("No breakpoint left for the test")
    if schema == 1 and (data["reset_halt"] not in OPENOCD_RESET_HALT
                        or data["reset_run"] not in OPENOCD_RESET_RUN):
        raise ValueError("Only OpenOCD reset halt/init/run is supported by schema 1")
    identity = data["identity"]
    if not isinstance(identity, dict) or set(identity) != {"address", "mask", "value"}:
        raise ValueError("Invalid identity description")
    if any(type(v) is not int or not 0 <= v <= 0xFFFFFFFF for v in identity.values()):
        raise ValueError("Invalid identity values")
    if not identity["mask"] or identity["value"] & ~identity["mask"]:
        raise ValueError("Invalid identity mask")
    registers = data["diagnostic_registers"]
    if not isinstance(registers, dict) or any(
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k) or type(v) is not int
            or not 0 <= v <= 0xFFFFFFFC or v % 4 for k, v in registers.items()):
        raise ValueError("Invalid diagnostic registers")
    if "flash_size_address" in data:
        address = data["flash_size_address"]
        if type(address) is not int or not 0 < address <= 0xFFFFFFFE or address % 2:
            raise ValueError("Invalid Flash size register address")
    validate_profile_keys(data)
    if schema == 2:
        validate_profile_sections(data)
    return data
