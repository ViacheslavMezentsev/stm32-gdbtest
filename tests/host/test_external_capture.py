"""Joint capture: subprocess lifecycle, clock eligibility and immutable raw results."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "tests/external-capture"
spec = importlib.util.spec_from_file_location("external_analysis", EXAMPLE / "analysis.py")
analysis = importlib.util.module_from_spec(spec)
spec.loader.exec_module(analysis)


class ExternalCaptureTests(unittest.TestCase):
    def test_process_campaign_and_reanalysis(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "campaign"
            proc = subprocess.run([sys.executable, str(EXAMPLE / "run.py"), "--output", str(out)],
                                  capture_output=True, text=True, timeout=45)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads((out / "summary.json").read_text())
            self.assertEqual(len(summary["results"]), 19)
            self.assertTrue(all(r["ok"] and r["cleanup"] == "VERIFIED" for r in summary["results"]))
            for row in summary["results"]:
                folder = out / row["case"]
                original = (folder / "scenario.json").read_bytes()
                again = analysis.analyze_files(folder)
                self.assertEqual(again["verdict"], row["analysis"]["verdict"])
                self.assertEqual((folder / "scenario.json").read_bytes(), original)
            normal = out / "normal"
            data = (normal / "external.jsonl").read_text()
            (normal / "external.jsonl").write_text(data.replace('"value": 20', '"value": 21'))
            result = analysis.analyze_files(normal)
            self.assertEqual(result["reason"], "artifact_invalid")
            self.assertIn("hash mismatch", result["detail"])

    def fixture(self):
        manifest = {"run": "run", "revision": "rev", "expected_count": 3, "tolerance_ticks": 2,
                    "clock": {"kind": "fixture_offset", "anchors": [[0, 1000], [40, 1040]], "uncertainty": 1}}
        scenario = {"run": "run", "revision": "rev", "status": "PASS",
                    "samples": [{"tick": n, "value": n} for n in (10, 20, 30)]}
        capture = {"status": "COMPLETE", "cleanup": "VERIFIED", "ready_ns": 1, "window_start_ns": 2, "closed_ns": 3}
        rows = [{"kind": "ready", "source": "fixture"}]
        rows += [{"kind": "sample", "source": "fixture", "run": "run", "revision": "rev", "unit": "unit",
                  "channel": "signal", "seq": i, "source_tick": n + 1000, "value": n} for i, n in enumerate((10, 20, 30))]
        rows += [{"kind": "end", "run": "run", "count": 3}]
        return manifest, scenario, capture, rows

    def test_uncertainty_interval_not_point_estimate(self):
        for offset, expected in ((0, "PASS"), (1, "PASS"), (2, "UNKNOWN"), (3, "UNKNOWN"), (4, "FAIL"), (-4, "FAIL")):
            with self.subTest(offset=offset):
                m, s, c, rows = self.fixture()
                rows[2]["source_tick"] += offset
                self.assertEqual(analysis.analyze(m, s, c, rows)["verdict"], expected)

    def test_readiness_and_cleanup_gate_analysis(self):
        for changes in ({"ready_ns": 4}, {"cleanup": "UNKNOWN"}, {"status": "INCOMPLETE"}):
            m, s, c, rows = self.fixture()
            c.update(changes)
            self.assertEqual(analysis.analyze(m, s, c, rows)["verdict"], "UNKNOWN")

    def test_analysis_does_not_mutate_inputs(self):
        inputs = self.fixture()
        original = copy.deepcopy(inputs)
        self.assertEqual(analysis.analyze(*inputs)["verdict"], "PASS")
        self.assertEqual(inputs, original)

    def test_unqualified_clock_and_missing_scenario_samples(self):
        for uncertainty in (float("nan"), float("inf"), -1, 3, True):
            m, s, c, rows = self.fixture()
            m["clock"]["uncertainty"] = uncertainty
            self.assertEqual(analysis.analyze(m, s, c, rows)["verdict"], "UNKNOWN")
        m, s, c, rows = self.fixture()
        s["samples"].pop()
        self.assertEqual(analysis.analyze(m, s, c, rows)["reason"], "scenario_samples")
