import json
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch
from types import SimpleNamespace

from stm32_gdbtest.collect import collect, trace
from stm32_gdbtest.processes import probe_lock
from stm32_gdbtest.openocd import load_stand, server_command
from stm32_gdbtest.profile import load_profile
from stm32_gdbtest.reports import write_reports
from stm32_gdbtest.runner import ROOT, run
from stm32_gdbtest.compatibility import REQUIRED_GDB_API, inspect_gdb_api, require_gdb_api, runtime_manifest
from stm32_gdbtest.backends import load_stand as load_backend_stand, server_spec


class HostTests(unittest.TestCase):
    def setUp(self):
        directory = ROOT / "build/host-tests"
        directory.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=directory)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_consumer_session_scopes_reports_and_rejects_escape(self):
        from stm32_gdbtest.runner import local_directory
        consumer = self.directory / "consumer"
        consumer.mkdir()
        session = dict(root=str(consumer), out=str(consumer / "build/runs"), stand="")
        test = dict(id="HW_CONSUMER", timeout_s=10)
        with patch.dict(os.environ, {}, clear=True), patch("stm32_gdbtest.runner.execute") as process:
            self.assertNotEqual(run(session, test), 0)
            process.assert_not_called()
        reports = list(consumer.glob("build/runs/*/result.json"))
        self.assertEqual(len(reports), 1)
        self.assertIn("Select a local stand", json.loads(reports[0].read_text())["error"])
        escaped = self.directory / "escaped"
        with self.assertRaises(ValueError):
            local_directory(escaped, consumer)
        self.assertFalse(escaped.exists())

    def test_legacy_stand_environment_is_not_silently_ignored(self):
        session = dict(root=str(self.directory), out=str(self.directory / "reports"))
        with patch.dict(os.environ, {"HWTEST_STAND": "old.toml"}), \
                patch("stm32_gdbtest.runner.load_stand") as load:
            self.assertEqual(run(session, dict(id="HW_LEGACY", timeout_s=10)), 2)
            load.assert_not_called()
        report = json.loads(next((self.directory / "reports").glob("*/result.json")).read_text())
        self.assertIn("Rename legacy environment", report["error"])

    def test_collection_does_not_execute_code(self):
        (self.directory / "test_one.py").write_text(
            'raise RuntimeError("must not import")\n@case("HW_ONE", labels=("gpio",))\ndef one(t): pass\n')
        cases = collect(self.directory)
        self.assertEqual(cases[0]["id"], "HW_ONE")

    def test_gdb_api_checks_do_not_infer_support_from_version(self):
        api = SimpleNamespace(VERSION="999.0")
        for name in REQUIRED_GDB_API:
            obj = api
            parts = name.split(".")
            for part in parts:
                if not hasattr(obj, part):
                    setattr(obj, part, SimpleNamespace())
                obj = getattr(obj, part)
        require_gdb_api(inspect_gdb_api(api))
        del api.Breakpoint.pending
        checks = inspect_gdb_api(api)
        self.assertFalse(checks["Breakpoint.pending"])
        with self.assertRaisesRegex(RuntimeError, "Breakpoint.pending"):
            require_gdb_api(checks)

    def test_manifest_extracts_versions_without_copying_private_log_data(self):
        log = ("Open On-Chip Debugger 0.12.0+dev (build)\n"
               "Info : STLINK V2J43M28 (API v2) VID:PID 0483:3752\n"
               "adapter serial PRIVATE_SERIAL\nC:/Users/PRIVATE_USER/tools\n")
        manifest = runtime_manifest(dict(gdb_version="14.2.90", python_version="3.11.4"), log)
        self.assertEqual(manifest["backend"]["version"], "0.12.0+dev")
        self.assertEqual(manifest["debugger"]["firmware"], "V2J43M28")
        self.assertEqual(manifest["debugger"]["api"], 2)
        self.assertNotIn("PRIVATE", json.dumps(manifest))
        self.assertEqual(manifest["gdb"]["python"], "3.11.4")

    def test_missing_runtime_evidence_is_explicit_not_success(self):
        manifest = runtime_manifest({}, "unrecognized backend banner")
        for section, key in (("gdb", "version"), ("backend", "version"), ("debugger", "firmware")):
            self.assertIsNone(manifest[section][key])
            self.assertTrue(manifest[section]["evidence"].startswith("unavailable:"))
        self.assertEqual(manifest["schema"], 1)
        self.assertIn("unavailable:", manifest["build"]["provenance"])

    def test_stlink_manifest_does_not_invent_openocd_api_version(self):
        manifest = runtime_manifest({"backend": "stlink"},
            "STMicroelectronics ST-LINK GDB server. Version 7.14.0\n"
            "ST-LINK Firmware version : V2J43M28\nSerial: PRIVATE\n")
        self.assertEqual(manifest["backend"]["name"], "stlink")
        self.assertEqual(manifest["backend"]["version"], "7.14.0")
        self.assertEqual(manifest["debugger"]["firmware"], "V2J43M28")
        self.assertIsNone(manifest["debugger"]["api"])
        self.assertNotIn("PRIVATE", json.dumps(manifest))

    def test_stlink_requires_programmer_and_rejects_unknown_settings(self):
        stand = self.directory / "stand.toml"
        content = '[probe]\nbackend="stlink"\nserial="TEST"\n'
        with patch("stm32_gdbtest.backends.shutil.which", return_value="server.exe"):
            stand.write_text(content)
            with self.assertRaisesRegex(ValueError, "programmer_dir"):
                load_backend_stand(stand)
            (self.directory / "STM32_Programmer_CLI.exe").touch()
            content += 'programmer_dir="' + self.directory.as_posix() + '"\n'
            stand.write_text(content + 'flash_policy="verify-only"\n')
            with self.assertRaisesRegex(ValueError, "Unknown probe setting"):
                load_backend_stand(stand)
            stand.write_text(content)
            loaded = load_backend_stand(stand)
            self.assertEqual(loaded["flash"], "if-different")
            self.assertEqual(loaded["backend"], "stlink")

    def test_backend_dialects_keep_vendor_commands_separate(self):
        profile = load_profile(ROOT / "Tests/fixtures/f103c8/target.toml")
        stand = dict(backend="stlink", executable="server.exe", programmer_dir="C:/ST/bin",
                     serial="TEST", speed_khz=1000)
        st = server_spec(stand, 1234, profile, self.directory)
        self.assertEqual(st["finish"], ["monitor reset", "detach"])
        self.assertNotIn(profile["openocd_target"], st["command"])
        self.assertIn(str(self.directory), st["command"])
        self.assertIn("-e", st["command"])
        self.assertIn("-g", st["command"])
        self.assertNotIn("--erase-all", st["command"])
        self.assertNotIn("-t", st["command"])
        oc = server_spec(dict(stand, backend="openocd"), 1234, profile, self.directory)
        self.assertEqual(oc["finish"], ["monitor reset run", "disconnect"])
        self.assertIn(profile["openocd_target"], oc["command"])

    def test_jlink_requires_serial_and_known_device_mapping(self):
        path = self.directory / "stand.toml"
        with patch("stm32_gdbtest.backends.shutil.which", return_value="JLinkGDBServerCL.exe"):
            for serial in ("0", "1", "nickname", "001234"):
                path.write_text('[probe]\nbackend="jlink"\nserial="' + serial + '"\n')
                with self.assertRaisesRegex(ValueError, "explicit decimal"):
                    load_backend_stand(path)
            path.write_text('[probe]\nbackend="jlink"\nserial="123456789"\n')
            stand = load_backend_stand(path)
        profile = load_profile(ROOT / "Tests/fixtures/f103c8/target.toml")
        spec = server_spec(stand, 1234, profile, self.directory)
        self.assertIn("STM32F103C8", spec["command"])
        self.assertIn("-nosinglerun", spec["command"])
        self.assertNotIn("-singlerun", spec["command"])
        self.assertEqual(spec["setup"], ["monitor flash breakpoints = 0"])
        self.assertEqual(spec["finish"], ["monitor reset", "monitor go", "disconnect"])
        with self.assertRaisesRegex(ValueError, "mapping not validated"):
            server_spec(stand, 1234, dict(profile, mcu="STM32H503CBT6"), self.directory)

    def test_jlink_runtime_version_and_firmware_are_separate(self):
        report = runtime_manifest({"backend": "jlink"},
            "SEGGER J-Link GDB Server V8.32 Command Line Version\n"
            "Firmware: J-Link V9 compiled May  7 2021 16:26:12\n"
            "S/N: PRIVATE\nCommand line: -USB PRIVATE\n")
        self.assertEqual(report["backend"]["version"], "8.32")
        self.assertEqual(report["debugger"]["firmware"], "J-Link V9 compiled May  7 2021 16:26:12")
        self.assertIsNone(report["debugger"]["api"])
        self.assertNotIn("PRIVATE", json.dumps(report))

    def test_profiles_select_distinct_mcus_and_flash_limits(self):
        f411ce = load_profile(ROOT / "Tests/fixtures/f411ce/target.toml")
        f103c8 = load_profile(ROOT / "Tests/fixtures/f103c8/target.toml")
        self.assertEqual((f411ce["flash_size"], f103c8["flash_size"]), (512 * 1024, 64 * 1024))
        self.assertNotEqual(f411ce["identity"]["value"], f103c8["identity"]["value"])
        stand = dict(executable="openocd", serial="TEST", speed_khz=1000)
        self.assertIn("target/stm32f1x.cfg", server_command(stand, 1234, f103c8))
        self.assertNotIn("target/stm32f4x.cfg", server_command(stand, 1234, f103c8))

    def test_profile_rejects_typo_and_missing_settings(self):
        source = (ROOT / "Tests/fixtures/f411ce/target.toml").read_text()
        path = self.directory / "target.toml"
        for old, new in (("flash_size", "flash_szie"), ('schema = 1', 'schema = 2'),
                         ('breakpoint_limit = 6', 'breakpoint_limit = 4'),
                         ('flash_size = 524288', 'flash_size = -1'),
                         ('flash_size_address = 0x1FFF7A22', 'flash_size_address = 3')):
            path.write_text(source.replace(old, new))
            with self.assertRaises(ValueError):
                load_profile(path)

    def test_duplicate_and_dynamic_metadata_rejected(self):
        p = self.directory / "test_bad.py"
        for source in ('@case(make_id())\ndef one(t): pass\n',
                       '@case("HW_ONE")\ndef one(t): pass\n@case("HW_ONE")\ndef two(t): pass\n'):
            p.write_text(source)
            with self.assertRaises(ValueError):
                collect(self.directory)

    def test_trace_rejects_missing_and_duplicate_requirements(self):
        p = self.directory / "requirements.md"
        for content in ("## HW_OTHER\n", "## HW_ONE\n## HW_ONE\n"):
            p.write_text(content)
            with self.assertRaises(ValueError):
                trace([{"id": "HW_ONE"}], p)

    def test_stand_rejects_misspelled_flash_policy(self):
        path = self.directory / "stand.toml"
        path.write_text('[probe]\nbackend="openocd"\nserial="TEST"\nflash_policy="verify-only"\n')
        with self.assertRaisesRegex(ValueError, "Unknown probe setting"):
            load_stand(path)

    def test_reports_distinguish_assertion_and_infrastructure(self):
        for status, tag in (("PASS", None), ("FAIL", "failure"), ("ERROR", "error")):
            report = dict(id="HW_ONE", status=status, duration_s=1.25, error='expected <x> & "y"')
            report["compatibility"] = runtime_manifest(report)
            report["warnings"] = ["DEV_ID mismatch 0x423 -> 0x431"]
            report["identity"] = dict(policy="warn", matches=False)
            write_reports(self.directory, report)
            root = ET.parse(self.directory / "junit.xml").getroot()
            case = root.find("testcase")
            self.assertEqual(root.attrib["failures"], str(int(status == "FAIL")))
            self.assertEqual(root.attrib["errors"], str(int(status == "ERROR")))
            if tag:
                self.assertIn(report["error"], case.find(tag).text)
            self.assertEqual(json.loads((self.directory / "result.json").read_text()), report)
            self.assertEqual(json.loads(case.find("system-out").text)["compatibility"], report["compatibility"])
            self.assertEqual(json.loads(case.find("system-out").text)["warnings"], report["warnings"])

    def test_missing_stand_is_error_with_reports(self):
        session = dict(out=str(self.directory), stand=str(self.directory / "absent.toml"))
        with patch.dict(os.environ, {"STM32_GDBTEST_STAND": ""}):
            code = run(session, {"id": "HW_ONE", "timeout_s": 1})
        self.assertEqual(code, 2)
        report = json.loads(next(self.directory.glob("*/result.json")).read_text())
        self.assertEqual(report["status"], "ERROR")
        self.assertEqual(report["compatibility"]["schema"], 1)
        self.assertIsNone(report["compatibility"]["backend"]["version"])
        self.assertTrue(next(self.directory.glob("*/junit.xml")).exists())

    @unittest.skipUnless(os.name == "nt", "Windows lock")
    def test_probe_lock_rejects_concurrent_owner_and_releases(self):
        with probe_lock(self.directory, "TESTSERIAL"):
            with self.assertRaises(RuntimeError):
                with probe_lock(self.directory, "TESTSERIAL"):
                    self.fail("Concurrent ownership")
        with probe_lock(self.directory, "TESTSERIAL"):
            pass


if __name__ == "__main__":
    unittest.main()
