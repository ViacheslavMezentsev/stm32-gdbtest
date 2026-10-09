"""A failed build must not use a stale session to program hardware."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


RUN_HW = Path(__file__).resolve().parents[1] / "firmware/run_hw.py"
SPEC = importlib.util.spec_from_file_location("run_hw_build_guard", RUN_HW)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class BuildGuardTests(unittest.TestCase):
    def test_failed_build_never_reuses_stale_session_or_repeats(self):
        for repeat in (1, 2):
            with self.subTest(repeat=repeat), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                firmware = root / "tests/firmware"
                policy = firmware / "profiles/f030r8/full-image.toml"
                policy.parent.mkdir(parents=True)
                policy.write_text("fill = 255\n", encoding="utf-8")
                stand = root / "stand.toml"
                stand.write_text('[probe]\nbackend = "openocd"\nflash = "if-different"\n', encoding="utf-8")
                stale_session = firmware / "build/hw-f030r8-stand/hwtest/session.json"
                stale_session.parent.mkdir(parents=True)
                stale_session.write_text('{"stale": true}\n', encoding="utf-8")
                command = Mock(return_value=SimpleNamespace(returncode=1))
                argv = ["run_hw.py", "--profile", "f030r8", "--stand", str(stand),
                        "--toolchain", str(root / "toolchain"), "--cube", str(root / "cube"),
                        "--steps", "build", "prepare", "boot", "--repeat", str(repeat)]

                with patch.object(MODULE, "ROOT", root), patch.object(MODULE, "FIRMWARE", firmware), \
                        patch.object(MODULE, "command", command), patch.object(sys, "argv", argv):
                    self.assertEqual(MODULE.main(), 1)

                # Only configure may run. In particular, the scenario CLI cannot use an
                # existing session.json, even if one happens to be present in the build tree.
                self.assertEqual(command.call_count, 1)
                output = root / "build/hw/f030r8-stand"
                if repeat == 1:
                    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
                    self.assertEqual([(item["step"], item["status"]) for item in summary["steps"]],
                                     [("build", "FAIL")])
                else:
                    soak = json.loads((output / "soak.json").read_text(encoding="utf-8"))
                    self.assertEqual(soak["iterations"], 1)
                    self.assertEqual(soak["accepted_iterations"], 0)
