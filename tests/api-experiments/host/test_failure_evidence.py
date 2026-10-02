"""Reject unrelated errors masquerading as successful fault/timeout experiments."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.failure_evidence import validate


class FailureEvidenceTests(unittest.TestCase):
    def fault_report(self):
        return dict(status='ERROR', error='gdb.error: sum_bytes interrupted', teardown='reset_run',
                    image_verified=True, checks=[dict(passed=True)], research=dict(fault=dict(
                        guard_hit=True, exception=3, dummy_count=1, bfar=0x20020000,
                        cfsr=0x8200, hfsr=0x40000000)))

    def test_fault_requires_all_evidence(self):
        report = self.fault_report()
        validate('HW_R10_FAULT', report, Path('.'))
        for field, value in [('guard_hit', False), ('exception', 0), ('dummy_count', 0),
                             ('bfar', 0), ('cfsr', 0), ('hfsr', 0)]:
            with self.subTest(field=field):
                invalid = copy.deepcopy(report)
                invalid['research']['fault'][field] = value
                with self.assertRaises(RuntimeError):
                    validate('HW_R10_FAULT', invalid, Path('.'))

    def test_fault_rejects_failed_checks_and_wrong_status(self):
        for field, value in [('checks', [dict(passed=False)]), ('checks', []), ('status', 'PASS'),
                             ('error', 'unrelated'), ('teardown', None), ('image_verified', False)]:
            with self.subTest(field=field, value=value):
                report = self.fault_report()
                report[field] = value
                with self.assertRaises(RuntimeError):
                    validate('HW_R10_FAULT', report, Path('.'))

    def test_timeout_requires_entry_and_recovery(self):
        report = dict(status='ERROR', error='TimeoutExpired', teardown='reset_run (host recovery)')
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            with self.assertRaises(RuntimeError):
                validate('HW_R10_TIMEOUT', report, directory)
            marker = directory / 'entered-call.json'
            good = dict(function='Default_Handler', dummy_count=1, instruction_hex='fee7', exception=0)
            marker.write_text(json.dumps(good))
            validate('HW_R10_TIMEOUT', report, directory)
            for field, value in [('function', 'main'), ('dummy_count', 0),
                                 ('instruction_hex', '0000'), ('exception', 3)]:
                marker.write_text(json.dumps(dict(good, **{field: value})))
                with self.assertRaises(RuntimeError):
                    validate('HW_R10_TIMEOUT', report, directory)
            marker.write_text(json.dumps(good))
            for field, value in [('error', 'other error'), ('teardown', 'reset_run'), ('status', 'PASS')]:
                with self.assertRaises(RuntimeError):
                    validate('HW_R10_TIMEOUT', dict(report, **{field: value}), directory)
