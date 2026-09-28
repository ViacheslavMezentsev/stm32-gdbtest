"""Stand diagnostics and the Linux stand lock without a debugger (TC-93…TC-95)."""
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from stm32_gdbtest import doctor
from stm32_gdbtest.toolchain import find_gdb

ROOT = Path(__file__).resolve().parents[2]


class DoctorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def device(self, name, vendor, product, serial, bus=1, dev=5, node=True):
        path = self.dir / "sys" / name
        path.mkdir(parents=True)
        for key, value in dict(idVendor=vendor, idProduct=product, product="Probe", serial=serial,
                               busnum=str(bus), devnum=str(dev)).items():
            (path / key).write_text(value + "\n")
        if node:
            file = self.dir / "dev" / f"{bus:03d}" / f"{dev:03d}"
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("")

    def test_usb_scan_reports_serial_and_access(self):
        # TC-94: ТЗ 5.17.3 — ST-Link and J-Link found in sysfs; other devices, ST CDC and hubs ignored.
        self.device("1-1", "0483", "3748", "066CFF494849877187252626", dev=5)
        self.device("1-2", "1366", "0101", "000069653773", dev=6, node=False)
        self.device("1-3", "046d", "c52b", "MOUSE", dev=7)
        self.device("1-4", "0483", "5740", "CDC", dev=8)
        self.device("1-5", "1366", "0105", "", dev=9)
        (self.dir / "sys/1-5/bDeviceClass").write_text("09\n")
        devices = doctor.usb_debuggers(self.dir / "sys", self.dir / "dev")
        self.assertEqual([d["kind"] for d in devices], ["ST-Link", "J-Link"])
        self.assertTrue(devices[0]["access"])
        self.assertFalse(devices[1]["access"])
        self.assertTrue(doctor._serial_matches(devices[1], dict(backend="jlink", serial="69653773")))
        self.assertTrue(doctor._serial_matches(devices[0], dict(backend="openocd", serial="066cff494849877187252626")))
        self.assertFalse(doctor._serial_matches(devices[0], dict(backend="jlink", serial="69653773")))

    def test_gdb_found_in_arm_toolchain_root(self):
        # TC-93: ТЗ 5.17.1 — the same toolchain as run_hw.py when PATH has no GDB.
        gdb = self.dir / "bin" / ("arm-none-eabi-gdb-py3" + (".exe" if os.name == "nt" else ""))
        gdb.parent.mkdir()
        gdb.write_text("")
        env = {"STM32_GDBTEST_GDB": "", "ARM_TOOLCHAIN_ROOT": str(self.dir)}
        with patch.dict(os.environ, env), patch("shutil.which", return_value=None):
            self.assertEqual(find_gdb(), str(gdb))

    def test_missing_gdb_fails_and_never_starts_a_server(self):
        # TC-93: ТЗ 5.17.1, 5.17.2 — FAIL gives exit 1; the doctor starts no GDB server.
        env = {"STM32_GDBTEST_GDB": str(self.dir / "absent-gdb"), "STM32_GDBTEST_LOCK_DIR": str(self.dir),
               "ARM_TOOLCHAIN_ROOT": "", "USERPROFILE": ""}
        with patch.dict(os.environ, env), patch("stm32_gdbtest.doctor.shutil.which", return_value=None), \
                patch("stm32_gdbtest.doctor.usb_debuggers", return_value=[]), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(doctor.main(), 1)
        self.assertRegex(out.getvalue(), r"FAIL gdb: GDB with Python not found")
        with patch.dict(os.environ, env), patch("stm32_gdbtest.doctor.shutil.which", return_value=None), \
                patch("stm32_gdbtest.doctor.usb_debuggers", return_value=[]):
            results = {r["name"]: r["status"] for r in doctor.diagnose()}
        self.assertEqual(results["cmake"], "WARN")
        self.assertNotIn("stand", results)


class LinuxStandLockTests(unittest.TestCase):
    def test_stand_lock_matches_ci_lock(self):
        # TC-95: ТЗ 6.10.4 — the stand uses the CI toolchain versions for both architectures.
        stand = json.loads((ROOT / "tools/linux-stand.lock.json").read_text(encoding="utf-8"))
        ci = json.loads((ROOT / "ci/dependencies.lock.json").read_text(encoding="utf-8"))
        components = {c["name"]: c for c in stand["components"]}
        self.assertEqual(set(components), {"python", "cmake", "ninja", "gcc", "openocd"})
        for component in stand["components"]:
            self.assertEqual(set(component["archives"]), {"x86_64", "aarch64"}, component["name"])
            for archive in component["archives"].values():
                self.assertRegex(archive["sha256"], r"^[0-9a-f]{64}$")
                self.assertTrue(archive["url"].startswith("https://github.com/"), archive["url"])
                self.assertIn(component["version"].split("+")[0], archive["url"])
        self.assertGreaterEqual(tuple(map(int, components["python"]["version"].split(".")[:2])), (3, 11))
        self.assertEqual(components["gcc"]["version"], ci["default_gcc"])
        self.assertEqual(components["cmake"]["version"], ci["default_cmake"])
        self.assertEqual(components["ninja"]["version"], ci["ninja_version"])
        ci_archives = {a["url"]: a["sha256"] for a in ci["archives"]}
        for component in stand["components"]:
            url = component["archives"]["x86_64"]["url"]
            if url in ci_archives:
                self.assertEqual(ci_archives[url], component["archives"]["x86_64"]["sha256"])
        sources = {s["name"] for s in ci["sources"]}
        self.assertTrue(set(stand["cube_sources"]) <= sources)
        self.assertTrue(all(re.match(r"Cube", name) for name in stand["cube_sources"]))


if __name__ == "__main__":
    unittest.main()
