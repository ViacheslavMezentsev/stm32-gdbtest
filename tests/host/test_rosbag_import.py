"""ROS1 bag v2 offline adapter: strict reader, neutral import, separate analysis, negative copies."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "tests/rosbag-import"


def load(name):
    spec = importlib.util.spec_from_file_location(f"rosbag_import_{name}", EXAMPLE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


rosbag1 = load("rosbag1")
fixture = load("fixture")
importer = load("importer")
analysis = load("analysis")


class RosbagImportTests(unittest.TestCase):
    def test_campaign_and_reanalysis(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "campaign"
            proc = subprocess.run([sys.executable, str(EXAMPLE / "run.py"), "--output", str(out)],
                                  capture_output=True, text=True, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["status"], "PASS")
            self.assertEqual(len(summary["results"]), 23)
            verdicts = [row["analysis"] for row in summary["results"]]
            self.assertEqual((verdicts.count("PASS"), verdicts.count("FAIL"), verdicts.count("UNKNOWN")), (3, 1, 19))
            normal = out / "normal"
            source = (normal / "source.bag").read_bytes()
            self.assertEqual(analysis.analyze_files(normal)["verdict"], "PASS")
            self.assertEqual((normal / "source.bag").read_bytes(), source)
            text = (normal / "samples.jsonl").read_text(encoding="utf-8")
            (normal / "samples.jsonl").write_text(text.replace('"value": 2.5', '"value": 2.6', 1), encoding="utf-8")
            tampered = analysis.analyze_files(normal)
            self.assertEqual(tampered["reason"], "artifact_invalid")
            self.assertIn("hash mismatch", tampered["detail"])

    def test_reader_values_and_compression(self):
        plain = rosbag1.read(fixture.build("normal")[0])
        packed = rosbag1.read(fixture.build("bz2")[0])
        self.assertEqual(plain["compression"], ["none"])
        self.assertEqual(packed["compression"], ["bz2"])
        strip = [(m["conn"], m["time_ns"], m["value"]) for m in plain["messages"]]
        self.assertEqual(strip, [(m["conn"], m["time_ns"], m["value"]) for m in packed["messages"]])
        uptime = [m["value"] for m in plain["messages"] if m["conn"] == 0]
        self.assertEqual(uptime[0], 2)
        self.assertEqual(uptime[-1], 11)
        self.assertEqual(sorted(set(m["value"] for m in plain["messages"] if m["conn"] == 1)), [1.25, 2.5, 3.75, 5.0])

    def test_corruptions_never_return_partial_data(self):
        for variant, reason in (("truncated", "truncated"), ("unindexed", "unindexed"),
                                ("index_mismatch", "index_mismatch"), ("lz4", "unsupported_compression")):
            with self.subTest(variant=variant):
                with self.assertRaises(rosbag1.BagError) as error:
                    rosbag1.read(fixture.build(variant)[0])
                self.assertEqual(error.exception.reason, reason)
        blob = fixture.build("normal")[0]
        # Любой обрыв файла — ошибка, а не укороченный набор сообщений.
        for cut in range(1, len(blob), 97):
            with self.subTest(cut=cut), self.assertRaises(rosbag1.BagError):
                rosbag1.read(blob[:cut])
        flipped = bytearray(blob)
        flipped[:4] = b"#RAS"
        with self.assertRaises(rosbag1.BagError) as error:
            rosbag1.read(bytes(flipped))
        self.assertEqual(error.exception.reason, "not_bag_v2")

    def test_import_keeps_constant_values_and_marks_nonfinite(self):
        doc, lines = importer.import_bag(fixture.build("normal")[0], {"/demo/sensor/reference_v": {"name": "ref",
                                                                                                    "unit": "V"}})
        rows = [json.loads(line) for line in lines]
        ref = [row for row in rows if row["channel"] == "ref"]
        self.assertEqual(len(ref), fixture.COUNT)
        self.assertEqual({row["value"] for row in ref}, {1.0})
        self.assertEqual([row["seq"] for row in ref], list(range(fixture.COUNT)))
        self.assertEqual(doc["clock"]["record_time"]["name"], "ros1_record_time")
        undeclared = [c for c in doc["channels"] if c["name"] == "/demo/state/mode"]
        self.assertEqual(undeclared[0]["unit"], None)
        doc, lines = importer.import_bag(fixture.build("nan")[0], {})
        bad = [json.loads(line) for line in lines if '"nonfinite"' in line]
        self.assertEqual(len(bad), 1)
        self.assertIsNone(bad[0]["value"])
        self.assertEqual(bad[0]["nonfinite"], "nan")
        self.assertEqual(sum(c["nonfinite"] for c in doc["channels"]), 1)

    def test_anchor_segments(self):
        def rows(*pairs):
            return [{"t_ns": t, "value": v} for t, v in pairs]
        segments = analysis.anchors(rows((0, 3), (5, 3), (10, 4), (20, 6), (30, 7), (40, 2), (50, 3)))
        self.assertEqual([(s["first"], s["last"]) for s in segments], [(3, 7), (2, 3)])
        self.assertEqual(segments[0]["anchors"], {4: (5, 10), 7: (20, 30)})
        self.assertEqual(segments[1]["anchors"], {3: (40, 50)})

    def test_analysis_does_not_mutate_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "campaign"
            subprocess.run([sys.executable, str(EXAMPLE / "run.py"), "--output", str(out)],
                           capture_output=True, text=True, timeout=120, check=True)
            folder = out / "normal"
            names = analysis.FILES
            values = [json.loads((folder / n).read_text(encoding="utf-8")) if n != "samples.jsonl" else
                      [json.loads(line) for line in (folder / n).read_text(encoding="utf-8").splitlines()]
                      for n in names]
            original = copy.deepcopy(values)
            self.assertEqual(analysis.analyze(*values)["verdict"], "PASS")
            self.assertEqual(values, original)
            # Задержка без измерения в локальной записи не даёт PASS даже при совпадении значений.
            manifest = copy.deepcopy(values[0])
            manifest["scope"] = "local_recording"
            self.assertEqual(analysis.analyze(manifest, *values[1:])["reason"], "clock_assumed")
            manifest["clock"]["max_latency_ms"] = float("nan")
            self.assertEqual(analysis.analyze(manifest, *values[1:])["reason"], "clock_unqualified")

    def test_local_mode_converts_and_sanitizes_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            blob, summary = fixture.build("normal")
            (temp / "rec.bag").write_bytes(blob)

            def utc(ns):
                return datetime.fromtimestamp(ns // 1_000_000_000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S") + \
                    f".{ns % 1_000_000_000 // 1000:06d}Z"
            meta = {"test": "DEMO_TELEMETRY", "status": "PASS", "port": "/dev/serial/by-id/private",
                    "record_start_utc": utc(fixture.T0 - 10**9), "record_stop_utc": utc(fixture.T0 + 11 * 10**9),
                    "bag": {"messages": summary["messages"], "size": len(blob), "start": summary["start_ns"] / 1e9,
                            "end": summary["end_ns"] / 1e9, "topics": [{"topic": t} for t in summary["topics"]]}}
            (temp / "rec.json").write_text(json.dumps(meta), encoding="utf-8")
            (temp / "result.json").write_text(json.dumps({"id": "DEMO_TELEMETRY", "status": "PASS", "run_id": "r1",
                                                          "mode": "hardware"}), encoding="utf-8")
            records = {"run_id": "r1", "case_id": "DEMO_TELEMETRY",
                       "records": [{"name": "debug_values", "data": {"level": 2.5, "reference": 1.0, "tick": 5200}}]}
            (temp / "records.json").write_text(json.dumps(records), encoding="utf-8")
            run = load("run")
            manifest = copy.deepcopy(run.MANIFEST)
            manifest.update(scope="local_recording", clock={"max_latency_ms": 20, "basis": "measured"})
            contract = {"channels": run.CHANNELS, "manifest": manifest, "expected": ["PASS", "correlated"]}
            (temp / "contract.json").write_text(json.dumps(contract), encoding="utf-8")
            out = temp / "out"
            proc = subprocess.run([sys.executable, str(EXAMPLE / "run.py"), "--output", str(out),
                                   "--bag", str(temp / "rec.bag"), "--capture", str(temp / "rec.json"),
                                   "--result", str(temp / "result.json"), "--records", str(temp / "records.json"),
                                   "--contract", str(temp / "contract.json")],
                                  capture_output=True, text=True, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            capture = (out / "local/capture.json").read_text(encoding="utf-8")
            self.assertNotIn("private", capture)
            self.assertNotIn("port", json.loads(capture))
            partial = subprocess.run([sys.executable, str(EXAMPLE / "run.py"), "--bag", str(temp / "rec.bag")],
                                     capture_output=True, text=True, timeout=30)
            self.assertEqual(partial.returncode, 2)


if __name__ == "__main__":
    unittest.main()
