"""Lossless result history, audit failures and bounded deferred conversion."""
import copy
import io
import json
from pathlib import Path
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch
from stm32_gdbtest import report_data as r
from stm32_gdbtest.errors import ApiError, CheckFailed
from stm32_gdbtest.scenario import reject_failed_checks
from stm32_gdbtest.reports import write_reports


class ReportDataTests(unittest.TestCase):
    def report(self):
        data = dict(id='example', status='PASS', duration_s=0.1)
        r.configure(data, dict(report=dict(representation='compact', console='failures')))
        self.addCleanup(r.close, data)
        return data

    def test_long_history_and_middle_failure(self):
        for count in (1000, 10000):
            data = self.report()
            rows = [dict(name='same', actual=i, expected=i, passed=i != count//2) for i in range(count)]
            for row in rows:
                r.append(data, 'checks', row)
            self.assertLessEqual(len(data['checks'].pending), 128)
            self.assertGreater(data['checks'].spool_bytes, 0)
            encoded = r.payload(data, True)
            self.assertEqual(r.decode(encoded)['checks'], rows)
            streamed = r.decode(encoded, materialize=False)
            self.assertEqual(list(streamed['checks']), rows)
            with self.assertRaises(CheckFailed):
                reject_failed_checks(types.SimpleNamespace(report=streamed))

    def test_values_remain_distinct_and_snapshot_detached(self):
        data = self.report()
        row = dict(values=[0, False, None, 1, 1.0, ['r',0], {'ref':1}])
        r.append(data, 'evaluations', row)
        row['values'].append(2)
        restored = r.decode(r.payload(data, True))['evaluations'][0]['values']
        self.assertEqual([type(x) for x in restored[:5]], [int,bool,type(None),int,float])
        self.assertEqual(len(restored), 7)

    def test_late_repr_without_early_conversion(self):
        calls=[]
        class Opaque:
            def __repr__(self):
                calls.append(1)
                return 'late value'
        data=self.report()
        r.append(data,'checks',dict(name='opaque',passed=True,actual=Opaque()))
        reject_failed_checks(types.SimpleNamespace(report=data))
        self.assertEqual(calls,[])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'result.json'
            r.write(path,data)
            self.assertEqual(r.read(path)['checks'][0]['actual'],'late value')
        self.assertEqual(calls,[1])

    def test_limits_do_not_silently_drop_events(self):
        data=self.report()
        with patch.object(r,'MAX_DEFERRED',1):
            r.append(data,'checks',dict(actual=object()))
            with self.assertRaisesRegex(ApiError,'could not be saved'):
                r.append(data,'checks',dict(actual=object()))
        self.assertEqual(len(data['checks']),1)
        self.assertEqual(data['report_audit_error_count'],1)
        with self.assertRaises(ApiError):
            reject_failed_checks(types.SimpleNamespace(report=data))

    def test_primary_check_survives_disk_error(self):
        data=self.report()
        for i in range(128):
            r.append(data,'checks',dict(passed=True))
        data['checks'].stream.close()
        with self.assertRaises(CheckFailed) as caught:
            try:
                raise CheckFailed('primary',0,1)
            finally:
                r.append(data,'checks',dict(passed=False))
        self.assertIn('report_audit_error',caught.exception.details)
        self.assertEqual(data['report_audit_error_count'],1)

    def test_corruption_counts_hash_and_completeness_rejected(self):
        data=self.report()
        r.append(data,'checks',dict(passed=True))
        good=r.payload(data,True)
        mutations=[lambda d:d.update(report_schema=99),
                   lambda d:d['collections']['checks'].update(count=2),
                   lambda d:d['collections']['checks'].update(complete=False),
                   lambda d:d['collections']['checks']['blocks'][0].update(sha256='bad')]
        for mutate in mutations:
            bad=copy.deepcopy(good);mutate(bad)
            with self.assertRaises(ValueError):r.decode(bad)
        with patch.object(r,'EXPANDED_BYTES',1):
            with self.assertRaises(ValueError):r.decode(good)

    def test_atomic_failure_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'result.json';path.write_text('{"status":"PASS"}')
            with patch.object(r,'FILE_BYTES',5):
                with self.assertRaises(ValueError):r.write(path,dict(status='FAIL'))
            self.assertEqual(r.read(path)['status'],'PASS')
            self.assertEqual(list(Path(tmp).glob('.result-*')),[])
            path.write_text('{"status":"PASS","status":"FAIL"}')
            with self.assertRaises(ValueError):r.read(path)

    def test_junit_summary_and_storage_error(self):
        data=self.report()
        for i in range(129):r.append(data,'checks',dict(name='hidden',passed=True))
        with tempfile.TemporaryDirectory() as tmp:
            write_reports(tmp,data)
            xml=(Path(tmp)/'junit.xml').read_text()
            self.assertIn('checks_total',xml)
            self.assertNotIn('hidden',xml)
            data['checks'].stream.close()
            write_reports(tmp,data)
            self.assertIn('report_storage_error',r.read(Path(tmp)/'result.json'))
            self.assertIn('infrastructure',(Path(tmp)/'junit.xml').read_text())

    def test_summary_never_closes_timed_out_window(self):
        data=self.report()
        for op,outcome in [('resume','started'),('wait','timeout'),('wait','timeout')]:
            r.observe_execution(data,op,dict(outcome=outcome,generation=7),None)
        self.assertEqual(data['execution_summary']['window'],'open')
        self.assertEqual(data['execution_summary']['count'],3)
        r.observe_execution(data,'halt',dict(outcome='stopped',generation=7),None)
        self.assertEqual(data['execution_summary']['window'],'closed')

    def test_target_console_keeps_all_checks(self):
        from test_target_records import TargetRecordsTests
        fixture=TargetRecordsTests();fixture.setUp()
        data=self.report();target=fixture.module.Target(data,{},fixture.config)
        output=io.StringIO()
        with redirect_stdout(output):
            target.check('good',1,1)
            with self.assertRaises(CheckFailed):target.check('bad',0,1)
        self.assertNotIn('PASS',output.getvalue())
        self.assertIn('FAIL',output.getvalue())
        self.assertEqual(len(data['checks']),2)

    def test_reach_records_completed_frame(self):
        from test_target_navigation import NavigationTests
        fixture=NavigationTests();fixture.setUp();target=fixture.target()
        r.configure(target.report,dict(report=dict(representation='compact')))
        self.addCleanup(r.close,target.report)
        from test_target_navigation import FakeBreakpointEvent
        def execute(command, **kwargs):
            point = next(p for p in target.owned if p.temporary)
            event = FakeBreakpointEvent([types.SimpleNamespace(number=point.id, type=1)], 'breakpoint')
            for listener in fixture.listeners: listener(event)
            return ''
        fixture.gdb.execute = execute
        from gdb_parameters import install
        install(fixture.gdb)
        stop=target.reach('app_loop')
        self.assertIn('frame',target.report['stops'][-1])
        self.assertEqual(target.report['stops'][-1]['frame'],stop['stop']['frame'])

    def test_write_records_readback_on_success_and_failure(self):
        from test_target_read_write import ReadWriteTests
        fixture=ReadWriteTests();fixture.setUp();target=fixture.target()
        r.configure(target.report,dict(report=dict(representation='compact')))
        self.addCleanup(r.close,target.report)
        with self.assertRaises(ApiError): target.write('app_state.ticks',17)
        self.assertEqual(target.report['mutations'][-1]['after'],41)
        target.write('app_state.ticks',41)
        self.assertEqual(target.report['mutations'][-1]['after'],41)

    def test_policy_validation_and_capsule_roundtrip(self):
        from test_session_config import SessionConfigTests
        from stm32_gdbtest.configuration import ConfigError
        from stm32_gdbtest.config_transport import dumps, loads
        fixture=SessionConfigTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.write('api.toml','schema=2\n[report]\nrepresentation="compact"\nconsole="failures"\n')
        config=fixture.load('target="target.toml"\napi="api.toml"')
        self.assertEqual(loads(dumps(config)).config['api']['report']['console'],'failures')
        for content in ['schema=1\n[report]\nconsole="failures"',
                        'schema=2\n[report]\nconsole="quiet"',
                        'schema=2\n[report]\nunknown=true']:
            fixture.write('api.toml',content)
            with self.assertRaises(ConfigError):fixture.load('target="target.toml"\napi="api.toml"')

    def test_reference_expansion_budget_before_copy(self):
        from stm32_gdbtest.report_codec import pack, expand
        encoded=pack([dict(value='x'*100)]*128)
        with self.assertRaises(ValueError):expand(encoded,maximum_bytes=1000)

    def test_pending_bytes_flush_before_next_large_row(self):
        data=self.report()
        with patch.object(r,'PENDING_BYTES',100):
            for i in range(4):r.append(data,'checks',dict(value='x'*80))
        self.assertEqual(len(data['checks'].pending),1)
        self.assertEqual(len(list(data['checks'])),4)

    def test_coverage_and_full_export_preserve_middle_failure(self):
        from test_ddtt_coverage import DdttCoverageTests
        fixture=DdttCoverageTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.result['checks']=[dict(name='count advanced',passed=p) for p in (True,False,True)]
        path=fixture.save(fixture.result)
        r.write(path,fixture.result,compact=True)
        self.assertEqual(fixture.run_export(path)[0]['state'],'FAILED')
        full=path.parent/'full.json'
        r.write(full,r.read(path),compact=False)
        self.assertEqual(r.read(full)['checks'],fixture.result['checks'])
        fixture.result['report_audit_error_count']=1
        r.write(path,fixture.result,compact=True)
        self.assertEqual(fixture.run_export(path)[0]['state'],'UNKNOWN')

    def test_fault_survives_report_append_failure(self):
        from test_live_execution import LiveTests
        fixture=LiveTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        class Broken(list):
            def append(self,row):raise OSError('storage unavailable')
        fixture.target.report['stops']=Broken()
        fixture.live.resume();fixture.run_wait();fixture.stop('fault')
        self.assertEqual(fixture.errors[-1].code,'fault_stop')
        self.assertIn('report_audit_error',fixture.errors[-1].details)
        self.assertEqual(fixture.live.state(),'stopped')

    def test_cleanup_confirms_halt_despite_report_failure(self):
        from test_live_execution import LiveTests
        from stm32_gdbtest.execution import CoroutineRunner
        fixture=LiveTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        class Broken(list):
            def append(self,row):raise OSError('storage unavailable')
        fixture.target.report['stops']=Broken()
        fixture.target.halt=lambda timeout:fixture.live.wait(timeout,'halt')
        fixture.live.resume()
        runner=CoroutineRunner(fixture.live.cleanup(),fixture.g,fixture.errors.append)
        runner.start();fixture.drain();fixture.stop('signal','SIGINT')
        self.assertEqual(fixture.errors,[])
        self.assertEqual(fixture.live.state(),'stopped')
        self.assertEqual(fixture.target.report['status'],'ERROR')
        self.assertEqual(fixture.target.report['execution_cleanup_audit_error']['code'],'report_unavailable')
