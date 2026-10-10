"""Reject false-positive acceptance of the selected API 0.4.0 hardware campaign."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("api040_campaign", Path(__file__).resolve().parents[1] / "firmware/api040.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "result.json"
        self.identifier = "HW_CI_040_SKIP"
        raw = json.dumps(dict(case_id=self.identifier, run_id="one", records=[
            dict(sequence=1, name="capability", data={}), dict(sequence=2, name="optional.finally", data={})])).encode()
        self.path.with_name("records.json").write_bytes(raw)
        self.path.with_name("junit.xml").write_text('<testsuite><testcase><skipped message="disabled"/></testcase></testsuite>')
        self.report = dict(status="SKIP", command_code=77, skip_reason="disabled", run_id="one", checks=[dict(passed=True)],
                           image_verified=True, teardown="reset_run",
                           capture=dict(status="saved", completion="interrupted", count=2, sha256=hashlib.sha256(raw).hexdigest()))

    def check_report(self, code=77, enabled=False):
        self.path.write_text(json.dumps(self.report))
        return MODULE.validate_run(self.path, code, self.identifier, enabled)

    def test_expected_skip_is_accepted(self):
        self.assertEqual(self.check_report()["status"], "SKIP")

    def test_unexpected_skip_or_wrong_exit_is_rejected(self):
        for code, enabled in ((77, True), (0, False), (2, False)):
            with self.subTest(code=code, enabled=enabled), self.assertRaises(ValueError):
                self.check_report(code, enabled)

    def test_capture_and_teardown_failures_are_rejected(self):
        for key, value in (("image_verified", False), ("teardown", "failed"), ("checks", [])):
            with self.subTest(key=key), patch.dict(self.report, {key: value}), self.assertRaises(ValueError):
                self.check_report()
        for key, value in (("status", "error"), ("completion", "normal"), ("sha256", "0" * 64), ("count", 3)):
            with self.subTest(key=key), patch.dict(self.report['capture'], {key: value}), self.assertRaises(ValueError):
                self.check_report()

    def test_junit_disagreement_is_rejected(self):
        self.path.with_name("junit.xml").write_text('<testsuite><testcase/></testsuite>')
        with self.assertRaises(ValueError):
            self.check_report()

    def test_later_successful_export_cannot_mask_failed_hardware(self):
        def command(args, log):
            if args[0] == "run":
                workdir = Path(args[args.index("--workdir") + 1])
                workdir.mkdir(parents=True)
                (workdir / "result.json").write_text('{"status":"ERROR","command_code":2}')
                return 2
            return 0
        with patch.object(MODULE, "command", side_effect=command):
            code = MODULE.run(self.root / "on.zip", self.root / "off.zip", self.root / "stand.toml", self.root / "out")
        self.assertEqual(code, 1)
        summary = json.loads(next((self.root / "out").glob('*/summary.json')).read_text())
        self.assertEqual(summary['status'], 'ERROR')
        self.assertEqual(summary['processing'], dict(export=0, verify=0, report=0))
        self.assertEqual(len(summary['runs']), 1)


if __name__ == '__main__':
    unittest.main()
