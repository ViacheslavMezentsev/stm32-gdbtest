"""Neutral model regression: the same C++ source is used on host and in Renode."""
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class StatefulBufferTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("g++"), "host g++ required")
    def test_positive_and_mutation_controls(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tests/stateful-buffer/run.py"), "--host-only"],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scenario_inventory_and_style(self):
        from stm32_gdbtest.collect import collect
        cases = collect([ROOT / "tests/stateful-buffer"])
        self.assertEqual({c["id"] for c in cases},
                         {"HW_EMU_NEXT_COMPLETE", "HW_EMU_NEXT_TIMEOUT", "HW_EMU_RING_ORDER"})
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tests/host/test_scenario_style.py"),
                                 str(ROOT / "tests/stateful-buffer/test_buffer.py")],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
