"""A3.1: independent outcomes, strict completeness and a bounded reserve."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from stm32_gdbtest import evidence, report_data as r
from stm32_gdbtest.records import Journal, RecordError
from stm32_gdbtest.compact_records import CompactJournal
from stm32_gdbtest.errors import ApiError, CheckFailed
from stm32_gdbtest.scenario import reject_failed_checks, invoke_async
from stm32_gdbtest.result_capture import save, read, finalize
from stm32_gdbtest.reports import write_reports


class CompletenessTests(unittest.TestCase):
    def report(self, compact=True):
        report = dict(id='CASE', run_id='RUN', status='PASS', duration_s=0)
        r.configure(report, dict(report=dict(representation='compact' if compact else 'full')))
        self.addCleanup(r.close, report)
        return report

    def test_independent_failure_after_catching_storage_error(self):
        data = self.report()
        with patch.object(r, 'MAX_ROWS', 0), self.assertRaises(ApiError):
            r.append(data, 'checks', dict(name='lost', passed=False))
        self.assertEqual(data['check_accounting'], dict(total=1,failed=1,unclassified=0))
        with self.assertRaises(CheckFailed):
            reject_failed_checks(SimpleNamespace(report=data))
        restored = r.decode(r.payload(data, True))
        self.assertEqual(restored['checks'], [])
        self.assertEqual(restored['evidence']['stores']['checks']['lost'], 1)

    def test_success_with_missing_audit_cannot_finish_pass(self):
        data = self.report()
        with patch.object(r, 'MAX_ROWS', 0), self.assertRaises(ApiError):
            r.append(data, 'checks', dict(passed=True))
        with self.assertRaises(ApiError):
            reject_failed_checks(SimpleNamespace(report=data))

    def test_reserve_does_not_grow_unbounded(self):
        data = self.report()
        with patch.object(r, 'MAX_ROWS', 0):
            for _ in range(1000):
                with self.assertRaises(ApiError):
                    r.append(data, 'checks', dict(passed=True))
        meta = data['evidence']
        self.assertEqual(len(meta['diagnostics']), 16)
        self.assertEqual(meta['diagnostics_omitted'], 984)
        self.assertLessEqual(len(json.dumps(meta['diagnostics']).encode()), 65536)
        evidence.validate(data)
        with patch.object(evidence, 'MAX_DIAGNOSTIC_BYTES', 1):
            evidence.diagnostic(data, 'result', ValueError('bounded'))
        self.assertEqual(meta['diagnostics_omitted'], 985)

    def test_journal_limits_and_saved_prefix_full_and_compact(self):
        for kind in (Journal, CompactJournal):
            data = self.report()
            journal = kind(max_records=1)
            evidence.journal(data, journal.record, 'value', 1)
            with self.assertRaises(RecordError):
                evidence.journal(data, journal.record, 'value', 2)
            with tempfile.TemporaryDirectory() as tmp:
                save(tmp, data, SimpleNamespace(_journal=journal), 'normal')
                captured = read(tmp, data)
                self.assertEqual(captured['records'][0]['data'], 1)
                finalize(tmp, data, True)
                self.assertEqual(data['status'], 'PASS')
                self.assertEqual(data['command_code'], 2)
                self.assertEqual(data['capture']['status'], 'saved')

    def test_invalid_value_is_refusal_not_observation_loss(self):
        data = self.report()
        with self.assertRaises(RecordError):
            evidence.journal(data, Journal().record, 'bad', object())
        self.assertFalse(evidence.unavailable(data))
        self.assertEqual(data['evidence']['stores']['records']['attempted'], 0)

    def test_reader_rejects_forged_counts_types_and_completeness(self):
        data = self.report()
        r.append(data, 'checks', dict(passed=False))
        for key, value in [('saved', 0), ('attempted', True), ('state', 'truncated'), ('first_lost', 1)]:
            encoded = r.payload(data, True)
            encoded = copy.deepcopy(encoded)
            encoded['evidence']['stores']['checks'][key] = value
            with self.assertRaises(ValueError):
                r.decode(encoded)
        encoded = copy.deepcopy(r.payload(data, True))
        encoded['check_accounting']['failed'] = 0
        with self.assertRaises(ValueError):
            r.decode(encoded)

    def test_one_lost_check_cannot_have_two_outcomes_or_two_endpoints(self):
        data=self.report()
        r.append(data,'checks',dict(passed=True))
        r.append(data,'checks',dict(passed=True))
        with patch.object(r,'MAX_ROWS',2), self.assertRaises(ApiError):
            r.append(data,'checks',dict(passed=False))
        data['check_accounting']['unclassified']=1
        with self.assertRaises(ValueError):
            evidence.validate(data)
        data['check_accounting']['unclassified']=0
        data['evidence']['stores']['checks']['first_lost']=2
        with self.assertRaises(ValueError):
            evidence.validate(data)

    def test_legacy_does_not_gain_claim_of_completeness(self):
        data = dict(status='PASS',checks=[])
        self.assertNotIn('evidence', r.decode(data))

    def test_serialization_fallback_preserves_failed_count(self):
        data = self.report()
        for _ in range(129):
            r.append(data,'checks',dict(passed=False))
        data['checks'].stream.close()
        with tempfile.TemporaryDirectory() as tmp:
            write_reports(tmp, data)
            saved = r.read(Path(tmp)/'result.json')
            self.assertEqual(saved['check_accounting']['failed'],129)
            self.assertEqual(saved['evidence']['stores']['checks']['saved'],0)
            self.assertEqual(saved['command_code'],2)

    def test_capture_reader_rejects_mismatched_accounting(self):
        data=self.report(); journal=Journal()
        evidence.journal(data,journal.record,'value',1)
        with tempfile.TemporaryDirectory() as tmp:
            save(tmp,data,SimpleNamespace(_journal=journal),'normal')
            data['evidence']['stores']['records']['saved']=0
            with self.assertRaises(ValueError):
                read(tmp,data)


class AsyncCompletenessTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_caught_failure_without_row_still_fails(self):
        data = dict(checks=[])
        r.configure(data, dict(report=dict(representation='compact')))
        self.addCleanup(r.close, data)
        async def scenario(target):
            with patch.object(r, 'MAX_ROWS', 0):
                try:
                    r.append(target.report, 'checks', dict(passed=False))
                except ApiError:
                    pass
        with self.assertRaises(CheckFailed):
            await invoke_async(scenario, SimpleNamespace(report=data))
