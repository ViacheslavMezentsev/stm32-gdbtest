"""Stand environment diagnostics without a GDB server or target connection (ТЗ 5.17)."""

import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

from stm32_gdbtest import backends, remote as remote_host
from stm32_gdbtest.processes import FLAGS, lock_directory, probe_identity
from stm32_gdbtest.runner import tool

USB_VENDORS = {"0483": "ST-Link", "1366": "J-Link"}
# ST's vendor ID also covers application devices (e.g. 5740, a USB CDC port of a
# board firmware); only ST-Link product IDs are debuggers.
STLINK_PRODUCTS = {"3744", "3748", "374a", "374b", "374d", "374e", "374f", "3752", "3753",
                   "3754", "3755", "3757"}
GDB_PROBE = "python import sys, tomllib, gdb; print(gdb.VERSION, sys.version.split()[0])"


def _output(args, timeout=20):
    result = subprocess.run([str(a) for a in args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, errors="replace", timeout=timeout, creationflags=FLAGS)
    return result.returncode, result.stdout.strip()


def usb_debuggers(sysfs=Path("/sys/bus/usb/devices"), dev=Path("/dev/bus/usb")):
    """ST-Link and J-Link devices visible through sysfs with their device node access."""
    found = []
    for device in sorted(sysfs.glob("*")):
        try:
            vendor = (device / "idVendor").read_text().strip()
        except OSError:
            continue
        if vendor not in USB_VENDORS:
            continue

        def attribute(name):
            try:
                return (device / name).read_text(errors="replace").strip()
            except OSError:
                return ""
        if attribute("bDeviceClass") == "09":
            continue  # USB hub, e.g. the hub inside some J-Link models
        if vendor == "0483" and attribute("idProduct").lower() not in STLINK_PRODUCTS:
            continue
        node = None
        if attribute("busnum") and attribute("devnum"):
            node = dev / f"{int(attribute('busnum')):03d}" / f"{int(attribute('devnum')):03d}"
        found.append(dict(kind=USB_VENDORS[vendor], vendor=vendor, product_id=attribute("idProduct"),
                          product=attribute("product"), serial=attribute("serial"),
                          node=str(node) if node else None,
                          access=bool(node and os.access(node, os.R_OK | os.W_OK))))
    return found


def _serial_matches(device, stand):
    serial = device["serial"]
    if stand["backend"] == "jlink":
        return device["kind"] == "J-Link" and serial.isdigit() and int(serial) == int(stand["serial"])
    return device["kind"] == "ST-Link" and serial.upper() == stand["serial"].upper()


def diagnose(gdb=None, stand=None, sysfs=Path("/sys/bus/usb/devices")):
    results = []

    def add(name, status, detail):
        results.append(dict(name=name, status=status, detail=detail))
    arch = platform.machine()
    add("host", "OK", f"{platform.system()} {platform.release()} {arch}, Python {platform.python_version()}")
    if sys.version_info < (3, 11):
        add("python", "FAIL", "Python 3.11+ required for the host runner")

    gdb = gdb or os.environ.get("STM32_GDBTEST_GDB") or shutil.which("arm-none-eabi-gdb-py3") \
        or shutil.which("arm-none-eabi-gdb")
    if not gdb or not Path(gdb).is_file():
        add("gdb", "FAIL", "GDB with Python not found: set STM32_GDBTEST_GDB or put arm-none-eabi-gdb-py3 on PATH")
    else:
        code, text = _output([gdb, "-nx", "-batch", "-ex", GDB_PROBE])
        version = text.splitlines()[-1] if text else ""
        if code or not re.fullmatch(r"\S+ 3\.(1[1-9]|[2-9]\d)\S*", version):
            add("gdb", "FAIL", f"{gdb}: embedded Python 3.11+ with tomllib required ({version or text[-200:]})")
        else:
            add("gdb", "OK", f"{gdb}: GDB {version.split()[0]}, Python {version.split()[1]}")
        missing = [name for name in ("arm-none-eabi-objdump", "arm-none-eabi-objcopy")
                   if not Path(tool(gdb, name)).is_file()]
        add("binutils", "FAIL" if missing else "OK",
            ("missing next to GDB: " + ", ".join(missing)) if missing else str(Path(gdb).parent))

    for name, minimum in (("cmake", (3, 25)), ("ninja", None)):
        path = shutil.which(name)
        if not path:
            add(name, "WARN", "not on PATH: needed for the CMake/CTest integration only")
            continue
        code, text = _output([path, "--version"])
        numbers = re.search(r"(\d+)\.(\d+)", text)
        old = minimum and numbers and (int(numbers[1]), int(numbers[2])) < minimum
        add(name, "WARN" if code or old else "OK",
            f"{path}: {text.splitlines()[0] if text else ''}" + (" (3.25+ required)" if old else ""))

    if os.name == "nt":
        add("lock", "OK", "named mutex in the Windows session")
    else:
        directory = lock_directory()
        try:
            directory.mkdir(parents=True, exist_ok=True)
            writable = os.access(directory, os.W_OK)
        except OSError:
            writable = False
        add("lock", "OK" if writable else "FAIL", f"{directory}" + ("" if writable else ": not writable"))

    loaded = None
    if stand:
        try:
            loaded = backends.load_stand(stand)
            where = f" on {loaded['remote']['host']} over SSH" if loaded.get("remote") else ""
            add("stand", "OK", f"{loaded['backend']} {loaded['executable']}{where}")
        except Exception as error:  # reported as a diagnostic, not raised
            hint = ""
            if not backends.WINDOWS and "stlink" in Path(stand).read_text(errors="replace") \
                    and arch in ("aarch64", "arm64"):
                hint = "; ST-LINK GDB Server has no Linux arm64 build, use openocd"
            add("stand", "FAIL", f"{error}{hint}")
    if loaded and loaded.get("remote"):
        # ТЗ 5.18.6: the stand host is checked through the same SSH path the runner uses.
        _check_remote(loaded, add)
        return results
    if loaded and loaded["backend"] == "openocd":
        code, text = _output([loaded["executable"], "--version"])
        first = text.splitlines()[0] if text else ""
        code, text = _output([loaded["executable"], "-f", "interface/stlink.cfg", "-c", "shutdown"])
        add("openocd", "FAIL" if code else "OK",
            first + ("" if not code else ": interface/stlink.cfg not usable, OpenOCD 0.11+ required"))

    if sys.platform.startswith("linux"):
        devices = usb_debuggers(sysfs)
        for device in devices:
            add("usb", "OK" if device["access"] else "FAIL",
                f"{device['kind']} {device['vendor']}:{device['product_id']} {device['product']} "
                f"serial {device['serial'] or '?'} {device['node']}"
                + ("" if device["access"] else ": no read/write access, install udev rules"))
        if not devices:
            add("usb", "WARN", "no ST-Link or J-Link on USB")
        if loaded and not any(_serial_matches(d, loaded) for d in devices):
            add("usb", "WARN", f"no {loaded['backend']} debugger with the stand serial in sysfs "
                "(ST-Link/V2 may report a binary serial; the GDB server decides)")
    else:
        add("usb", "OK", "USB access is not checked on this OS")
    return results


def _check_remote(stand, add):
    remote = stand["remote"]
    config = remote_host.check_config(probe_identity(stand["serial"], stand["backend"]), stand["executable"])
    try:
        code, text = _output(remote_host.ssh_command(remote) + [remote_host.remote_script(remote, config)], timeout=40)
    except subprocess.TimeoutExpired:
        add("remote", "FAIL", f"{remote['host']}: SSH did not answer in 40 s")
        return
    result = remote_host.check_result(text)
    if not result:
        hint = remote_host.environment_hint(code) or "see the output"
        add("remote", "FAIL", f"{remote['host']}: {hint}: {text.strip()[-300:]}")
        return
    old = tuple(int(x) for x in result["python"].split(".")[:2]) < (3, 8)
    add("remote", "FAIL" if old else "OK",
        f"{remote['host']}: {result['machine']}, helper Python {result['python']}" + (" (3.8+ required)" if old else ""))
    add("remote-server", "OK" if result["executable"] else "FAIL",
        result["executable"] or f"{stand['executable']} not found on the stand host (check env_script or PATH)")
    add("remote-lock", "OK" if result["lock_writable"] else "FAIL", result["lock_dir"])
    for device in result["usb"]:
        add("remote-usb", "OK" if device["access"] else "FAIL",
            f"{device['kind']} {device['product_id']} serial {device['serial'] or '?'} {device['node']}"
            + ("" if device["access"] else ": no read/write access, install udev rules on the stand host"))
    if not any(_serial_matches(d, stand) for d in result["usb"]):
        add("remote-usb", "WARN", f"no {stand['backend']} debugger with the stand serial on the stand host")


def main(gdb=None, stand=None, as_json=False):
    import json
    results = diagnose(gdb, stand)
    if as_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for item in results:
            print(f"{item['status']:<4} {item['name']}: {item['detail']}")
    return 1 if any(item["status"] == "FAIL" for item in results) else 0
