"""Offline attempts must preserve earlier CI and hardware evidence (ТЗ 8.16)."""
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from ci import run_checks


class CiArtifactTests(unittest.TestCase):
    def test_timeout_keeps_partial_output_and_previous_log(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "command.log"
            log.write_text("earlier evidence\n", encoding="utf-8")
            error = subprocess.TimeoutExpired(["check"], 3, output=b"last started test\npartial\xff")
            with patch.object(run_checks.subprocess, "run", side_effect=error):
                with self.assertRaisesRegex(run_checks.CheckError, "timed out after 3s"):
                    run_checks.run(["check"], timeout=3, log=log)
            saved = log.read_text(encoding="utf-8")
            self.assertTrue(saved.startswith("earlier evidence\n"))
            self.assertIn("last started test", saved)
            self.assertIn("[timeout 3s]", saved)

    def test_each_invocation_keeps_its_own_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def checks(record):
                record("sample", lambda: "ok")
            with patch.object(run_checks, "ROOT", root), patch.object(run_checks, "OUT", root), \
                    patch.object(run_checks, "level_docs", checks), patch("sys.argv", ["checks", "docs"]):
                self.assertEqual(run_checks.main(), 0)
                first = run_checks.OUT
                summary = (first / "summary.json").read_bytes()
                self.assertEqual(run_checks.main(), 0)
                self.assertNotEqual(first, run_checks.OUT)
                self.assertEqual((first / "summary.json").read_bytes(), summary)
                self.assertEqual(json.loads(summary)["passed"], 1)

    def test_firmware_configure_cannot_remove_an_existing_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            firmware = root / "tests/firmware"
            old = firmware / "build/f030r8-gcc13.3.1/hwtest/runs/result.json"
            old.parent.mkdir(parents=True)
            old.write_text("original evidence", encoding="utf-8")
            with patch.object(run_checks, "FIRMWARE", firmware), patch.object(run_checks, "OUT", root / "attempt"), \
                    patch.object(run_checks, "run", side_effect=RuntimeError("configure stopped")) as command:
                with self.assertRaisesRegex(RuntimeError, "configure stopped"):
                    run_checks.firmware_pair("13.3.1-1.1", "f030r8")
                args = command.call_args.args[0]
                self.assertTrue(args[args.index("-B") + 1].is_relative_to(firmware / "build/ci/attempt"))
                self.assertEqual(old.read_text(encoding="utf-8"), "original evidence")
