"""Preparation mode: every host-side step before the GDB server, never the debugger."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from stm32_gdbtest.build_manifest import command_args
from stm32_gdbtest.profile import load_profile
from stm32_gdbtest.runner import ROOT, run, tool

SECTIONS = """
Sections:
Idx Name          Size      VMA       LMA       File off  Algn
  0 .isr_vector   00000010  08000000  08000000  00001000  2**2
                  CONTENTS, ALLOC, LOAD, READONLY, DATA
  1 .text         00000010  08000010  08000010  00001010  2**2
                  CONTENTS, ALLOC, LOAD, READONLY, CODE
"""
PROFILE = ROOT / "tests/fixtures/f103c8/target.toml"


class PrepareTests(unittest.TestCase):
    def setUp(self):
        parent = ROOT / "build/host-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.elf = self.root / "firmware.elf"
        self.elf.write_bytes(b"ELF fixture; binutils are mocked")
        self.session = dict(root=str(self.root), out=str(self.root / "runs"), elf=str(self.elf),
                            gdb=str(self.root / "bin/arm-none-eabi-gdb-py3"), profile=str(PROFILE), stand="")
        self.test = dict(id="HW_PREPARE", timeout_s=10, contracts=[])

    def tools(self):
        """Mock objdump/objcopy/GDB probe; objcopy writes a BIN matching the sections."""
        def check_output(args, **kwargs):
            return SECTIONS.encode()

        def run_tool(args, **kwargs):
            if "--gap-fill=0xFF" in args:
                Path(args[-1]).write_bytes(bytes(range(32)))
            return type("Process", (), {"returncode": 0})()
        return (patch("stm32_gdbtest.runner.subprocess.check_output", side_effect=check_output),
                patch("stm32_gdbtest.runner.subprocess.run", side_effect=run_tool))

    def report(self):
        return json.loads(next((self.root / "runs").glob("*/result.json")).read_text())

    def test_prepare_passes_without_stand_lock_server_or_connection(self):
        # TC-74: ТЗ 5.16.1–5.16.4
        output, tool_run = self.tools()
        with patch.dict(os.environ, {"STM32_GDBTEST_STAND": ""}), output, tool_run, \
                patch("stm32_gdbtest.runner.probe_lock") as lock, \
                patch("stm32_gdbtest.runner.subprocess.Popen") as popen:
            self.assertEqual(run(self.session, self.test, prepare_only=True), 0)
            lock.assert_not_called()
            popen.assert_not_called()
        report = self.report()
        self.assertEqual((report["status"], report["mode"]), ("PASS", "prepare"))
        self.assertFalse(report["connection_attempted"])
        self.assertFalse(report["hardware_accessed"])
        self.assertNotIn("backend", report)
        self.assertEqual(report["contracts"]["status"], "NOT_REQUESTED")
        self.assertEqual([r["name"] for r in report["image_verification"]["regions"]], [".isr_vector", ".text"])
        self.assertIn("image.bin", report["artifacts"])
        self.assertEqual(report["compatibility"]["schema"], 1)

    def test_prepare_with_stand_records_backend_and_rejects_unmapped_jlink(self):
        # TC-75: ТЗ 5.16.2, 6.5.1
        stand = dict(backend="jlink", serial="123456789", executable="JLinkGDBServerCL", speed_khz=1000,
                     flash="verify-only")
        for mcu, status in (("STM32F103C8T6", "PASS"), ("STM32H503CBT6", "ERROR")):
            profile = dict(load_profile(PROFILE), mcu=mcu)
            output, tool_run = self.tools()
            with self.subTest(mcu=mcu), output, tool_run, \
                    patch("stm32_gdbtest.runner.load_stand", return_value=stand), \
                    patch("stm32_gdbtest.configuration._target_from_snapshot", return_value=profile), \
                    patch("stm32_gdbtest.runner.subprocess.Popen") as popen:
                run(dict(self.session, out=str(self.root / mcu)), self.test, "stand.toml", prepare_only=True)
                popen.assert_not_called()
            report = json.loads(next((self.root / mcu).glob("*/result.json")).read_text())
            self.assertEqual(report["status"], status)
            self.assertEqual(report["backend"], "jlink")
            if status == "PASS":
                self.assertEqual(report["backend_commands"]["setup"], ["monitor flash breakpoints = 0"])
            else:
                self.assertIn("mapping not validated", report["error"])

    def test_prepare_failure_is_error_before_server(self):
        # TC-76: ТЗ 5.16.3, 7.1.2
        output, tool_run = self.tools()
        self.elf.unlink()
        with patch.dict(os.environ, {"STM32_GDBTEST_STAND": ""}), output, tool_run, \
                patch("stm32_gdbtest.runner.subprocess.Popen") as popen:
            self.assertEqual(run(self.session, self.test, prepare_only=True), 2)
            popen.assert_not_called()
        self.assertEqual(self.report()["status"], "ERROR")

    def test_hardware_run_takes_debugger_lock_on_every_host(self):
        # TC-77: ТЗ 5.3.4 (р.0.7) — Windows and Linux both reach the lock and the run.
        stand = dict(backend="openocd", serial="TEST", executable="openocd", speed_khz=1000, flash="if-different")
        with patch("stm32_gdbtest.runner.load_stand", return_value=stand), \
                patch("stm32_gdbtest.runner.probe_lock") as lock, \
                patch("stm32_gdbtest.runner.execute") as execute:
            run(self.session, self.test, "stand.toml")
            lock.assert_called_once()
            self.assertEqual(lock.call_args.args[1:], ("TEST", "openocd"))
            execute.assert_called_once()
            self.assertNotIn("prepare_only", execute.call_args.kwargs)

    def test_bin_uses_only_selected_load_sections(self):
        # TC-87: ТЗ 4.1.5 — an empty .data with a RAM LMA must not reach objcopy.
        sections = SECTIONS + """  2 .data         00000000  20000000  20000000  00001030  2**0
                  CONTENTS, ALLOC, LOAD, DATA
"""
        calls = []

        def run_tool(args, **kwargs):
            calls.append([str(a) for a in args])
            if "--gap-fill=0xFF" in args:
                Path(args[-1]).write_bytes(bytes(range(32)))
            return type("Process", (), {"returncode": 0})()
        with patch.dict(os.environ, {"STM32_GDBTEST_STAND": ""}), \
                patch("stm32_gdbtest.runner.subprocess.check_output", return_value=sections.encode()), \
                patch("stm32_gdbtest.runner.subprocess.run", side_effect=run_tool):
            self.assertEqual(run(self.session, self.test, prepare_only=True), 0)
        objcopy = next(c for c in calls if "--gap-fill=0xFF" in c)
        selected = [objcopy[i + 1] for i, item in enumerate(objcopy) if item == "-j"]
        self.assertEqual(selected, [".isr_vector", ".text"])

    def test_binutils_follow_gdb_suffix_and_posix_command_lines(self):
        # TC-78: ТЗ 5.14.6, 6.2.1
        self.assertTrue(tool("C:/xpack/bin/arm-none-eabi-gdb-py3.exe", "arm-none-eabi-objdump").endswith(
            "arm-none-eabi-objdump.exe"))
        self.assertEqual(Path(tool("/opt/xpack/bin/arm-none-eabi-gdb-py3", "arm-none-eabi-objcopy")).name,
                         "arm-none-eabi-objcopy")
        if os.name != "nt":
            self.assertEqual(command_args("gcc -DNAME=\\\"a\\ b\\\" '-I/dir with space' -c x.c"),
                             ["gcc", '-DNAME="a b"', "-I/dir with space", "-c", "x.c"])


if __name__ == "__main__":
    unittest.main()
