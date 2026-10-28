"""Per-collection quotas preserve independent verdicts and stored prefixes."""
import copy
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from stm32_gdbtest import evidence, report_data as r
from stm32_gdbtest.errors import ApiError, CheckFailed
from stm32_gdbtest.scenario import reject_failed_checks
from stm32_gdbtest.records import Journal
from stm32_gdbtest.result_capture import save, read as capture, finalize
from stm32_gdbtest.reports import write_reports
from stm32_gdbtest.report_summary import read as summary

class ReportQuotaTests(unittest.TestCase):
    def report(self, representation='full', policy='truncate', limit=2, journal='error'):
        data=dict(id='CASE',run_id='RUN',status='PASS',duration_s=0)
        r.configure(data,dict(schema=3,report=dict(representation=representation,
            console='summary',on_limit=policy,max_rows_per_collection=limit),
            journal=dict(on_limit=journal)))
        self.addCleanup(r.close,data)
        return data

    def test_each_collection_independent_prefix_and_one_diagnostic(self):
        for representation in ('full','compact'):
            data=self.report(representation)
            for name in r.COLLECTIONS:
                for i in range(10):r.append(data,name,dict(index=i,passed=True))
                self.assertEqual([x['index'] for x in data[name]],[0,1])
                self.assertEqual(data['evidence']['stores'][name],dict(state='truncated',attempted=10,
                    saved=2,lost=8,first_lost=3,last_lost=10))
            self.assertEqual(data['evidence']['diagnostics_total'],6)
            evidence.validate(data)
            reject_failed_checks(SimpleNamespace(report=data))

    def test_strict_full_and_compact_cannot_catch_away_loss(self):
        for representation in ('full','compact'):
            data=self.report(representation,'error',1)
            r.append(data,'checks',dict(passed=True))
            with self.assertRaises(ApiError):r.append(data,'checks',dict(passed=True))
            self.assertEqual(data['evidence']['stores']['checks']['state'],'unavailable')
            with self.assertRaises(ApiError):reject_failed_checks(SimpleNamespace(report=data))

    def test_failed_check_missing_from_prefix_remains_fail(self):
        data=self.report(limit=1)
        r.append(data,'checks',dict(passed=True))
        r.append(data,'checks',dict(passed=False))
        self.assertTrue(all(x['passed'] for x in data['checks']))
        with self.assertRaises(CheckFailed):reject_failed_checks(SimpleNamespace(report=data))
        self.assertEqual(r.summary(data)['checks_failed'],1)
        self.assertEqual(r.summary(data)['checks_total'],2)

    def test_combinations_roundtrip_summary_and_capture(self):
        for representation in ('full','compact'):
            for journal_policy in ('error','truncate'):
                data=self.report(representation,journal=journal_policy)
                journal=Journal(max_records=1);journal.on_limit=journal_policy
                for i in range(4):r.append(data,'checks',dict(passed=True))
                evidence.journal(data,journal.record,'one',1)
                if journal_policy=='truncate':evidence.journal(data,journal.record,'two',2)
                with tempfile.TemporaryDirectory() as tmp:
                    save(tmp,data,SimpleNamespace(_journal=journal),'normal')
                    finalize(tmp,data,True);write_reports(tmp,data)
                    restored=r.read(Path(tmp)/'result.json')
                    self.assertEqual(restored['status'],'PASS')
                    self.assertEqual(restored['command_code'],2)
                    self.assertEqual(capture(tmp,restored)['records'][0]['data'],1)
                    self.assertEqual(summary(Path(tmp)/'result.json')['analysis'],'partial')
                    self.assertEqual(restored['evidence']['policy'], 'both-truncate' if journal_policy=='truncate' else 'report-truncate')

    def test_no_records_still_has_valid_capture(self):
        data=self.report()
        with tempfile.TemporaryDirectory() as tmp:
            save(tmp,data,SimpleNamespace(_journal=Journal()),'normal')
            self.assertEqual(capture(tmp,data)['records'],[])
            finalize(tmp,data,True)
            self.assertEqual(data['command_code'],0)

    def test_storage_error_is_not_quota_truncation(self):
        data=self.report('compact',limit=500)
        for _ in range(128):r.append(data,'checks',dict(passed=True))
        data['checks'].stream.close()
        with self.assertRaises(ApiError):r.append(data,'checks',dict(passed=True))
        self.assertEqual(data['evidence']['stores']['checks']['state'],'unavailable')

    def test_primary_error_survives_strict_limit(self):
        data=self.report(policy='error',limit=1)
        r.append(data,'checks',dict(passed=True))
        with self.assertRaises(CheckFailed):
            try:raise CheckFailed('primary',False,True)
            finally:r.append(data,'checks',dict(passed=False))
        self.assertEqual(data['check_accounting']['failed'],1)
        self.assertEqual(data['report_audit_error_count'],1)

    def test_reader_rejects_wrong_policy_and_nonprefix(self):
        data=self.report(limit=1)
        for i in range(3):r.append(data,'checks',dict(passed=True))
        for policy in ('journal-truncate','error'):
            bad=copy.deepcopy(r.payload(data,False));bad['evidence']['policy']=policy
            with self.assertRaises(ValueError):r.decode(bad)
        bad=copy.deepcopy(r.payload(data,False));bad['evidence']['stores']['checks']['first_lost']=1
        with self.assertRaises(ValueError):r.decode(bad)

    def test_no_repr_for_dropped_lazy_payload(self):
        class Opaque:
            def __repr__(self):raise AssertionError('repr not allowed')
        for representation in ('full','compact'):
            data=self.report(representation,limit=1)
            r.append(data,'evaluations',dict(value=1))
            r.append(data,'evaluations',dict(value=Opaque()))
            r.decode(r.payload(data,representation=='compact'))

    def test_serialization_failure_after_truncation_escalates(self):
        data=self.report('compact',limit=130)
        for i in range(131):r.append(data,'checks',dict(passed=True))
        first=copy.deepcopy(data['evidence']['diagnostics'][0])
        data['checks'].stream.close()
        with tempfile.TemporaryDirectory() as tmp:
            write_reports(tmp,data)
            restored=r.read(Path(tmp)/'result.json')
            self.assertEqual(restored['evidence']['stores']['checks']['state'],'unavailable')
            self.assertEqual(restored['evidence']['diagnostics'][0],first)
            self.assertEqual(restored['check_accounting']['total'],131)
            self.assertEqual(restored['command_code'],2)
