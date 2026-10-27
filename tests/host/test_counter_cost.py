"""Neutral model regression: the same C++ source is used on host and in Renode."""
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]


class CounterCostTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("g++"), "host g++ required")
    def test_positive_and_mutation_controls(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tests/counter-cost/run.py"), "--host-only"],
                                cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_scenario_inventory_and_style(self):
        from stm32_gdbtest.collect import collect
        cases = collect([ROOT / "tests/counter-cost"])
        self.assertEqual({c["id"] for c in cases},
                         {"HW_EMU_COUNTER_WRAP", "HW_EMU_COUNTER_UNKNOWN", "HW_EMU_COUNTER_COST", "HW_EMU_COUNTER_TRANSPORT"})
        result = subprocess.run([sys.executable, "-B", str(ROOT / "tests/host/test_scenario_style.py"),
                                 str(ROOT / "tests/counter-cost/test_counter.py")],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class CounterAnalysisTests(unittest.TestCase):
    def test_missing_corrupt_and_valid_transport(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("counter_analysis", ROOT / "tests/counter-cost/analysis.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        row = {"samples_ns": [100, 3, 5, 4, 8, 1], "warmup_count": 1,
               "scope": "host_gdb_roundtrip", "wcet": False, "median_ns": 4, "max_ns": 8}
        valid = [{"name": "host_latency", "data": row}]
        self.assertEqual(module.transport_summary(valid)["status"], "VALID")
        invalid = [[], valid + valid]
        for replacement in ({"samples_ns": [1]}, {"median_ns": 99}, {"wcet": True},
                            {"samples_ns": [True, 3, 5, 4, 8, 1]}, {"warmup_count": 2}):
            invalid.append([{"name": "host_latency", "data": dict(row, **replacement)}])
        for records in invalid:
            with self.subTest(records=records), self.assertRaises(ValueError):
                module.transport_summary(records)
