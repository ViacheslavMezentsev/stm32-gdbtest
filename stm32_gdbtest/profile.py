"""Validated target description; no implicit fallback to a different MCU."""

from pathlib import Path
import re
import tomllib


def load_profile(path):
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    required = {"schema", "name", "mcu", "openocd_target", "flash_start", "flash_size",
                "breakpoint_limit", "fault_handlers", "core_registers", "reset_halt",
                "reset_run", "identity", "diagnostic_registers"}
    if not required <= set(data) or set(data) - required - {"flash_size_address"} or type(data["schema"]) is not int or data["schema"] != 1:
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
    if data["reset_halt"] != "monitor reset halt" or data["reset_run"] != "monitor reset run":
        raise ValueError("Only OpenOCD reset halt/run is supported by schema 1")
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
    return data
