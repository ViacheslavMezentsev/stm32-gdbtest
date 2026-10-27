"""Neutral model regression: the same C++ source is used on host and in Renode."""
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class LogicalTimeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("g++"), "host g++ required")
    def test_positive_and_mutation_controls(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tests/logical-time/run.py"), "--host-only"],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scenario_inventory_and_style(self):
        from stm32_gdbtest.collect import collect
        cases = collect([ROOT / "tests/logical-time"])
        self.assertEqual({c["id"] for c in cases},
                         {"HW_EMU_TIME_THRESHOLD", "HW_EMU_TIME_WRAP", "HW_EMU_TIME_RETRY", "HW_EMU_TIME_REJECT"})
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tests/host/test_scenario_style.py"),
                                 str(ROOT / "tests/logical-time/test_time.py")],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
