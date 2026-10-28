"""A2.3 views are derived from complete evidence, never substitutes for it."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stm32_gdbtest import report_data, report_summary as summary
from stm32_gdbtest.reports import write_reports


class SummaryTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.path=self.root/'result.json'
        self.report=dict(id='ONE',run_id='run',status='PASS',command_code=0,duration_s=0,
                         checks=[dict(name='same',passed=True,expected=1)],cleanup='VERIFIED')

    def save(self, rows=(), compact=False):
        records=[dict(sequence=i+1,name='execution',data=row) for i,row in enumerate(rows)]
        raw=json.dumps(dict(schema=1,run_id='run',case_id='ONE',records=records)).encode()
        (self.root/'records.json').write_bytes(raw)
        self.report['capture']=dict(status='saved',completion='normal',path='records.json',
                                   sha256=hashlib.sha256(raw).hexdigest(),count=len(records))
        report_data.write(self.path,self.report,compact=compact)

    def test_same_meaning_across_storage_and_middle_failure(self):
        self.report['checks']=[dict(name='same',passed=i!=5000,actual=i,expected=i) for i in range(10000)]
        outputs=[]
        for compact in (False,True):
            self.save(compact=compact);before=self.path.read_bytes();view=summary.write(self.path)
            self.assertEqual(self.path.read_bytes(),before)
            self.assertEqual(summary.read(self.path),view)
            outputs.append(view['collections'])
            checks=view['collections']['checks']
            self.assertEqual(checks['failed'],1)
            self.assertTrue(checks['groups'][0]['different_expectations'])
            self.assertEqual(checks['groups'][0]['references'][0]['index'],5000)
        self.assertEqual(outputs[0],outputs[1])

    def test_wait_timeout_does_not_close_and_generations_separate(self):
        self.save([dict(operation='resume',outcome='started',generation=1),
                   dict(operation='wait',outcome='timeout',generation=1),
                   dict(operation='resume',outcome='started',generation=2),
                   dict(operation='halt',outcome='stopped',generation=2)])
        view=summary.build(self.path)
        self.assertEqual(view['execution']['states'],dict(open=1,closed=1,unknown=0))
        self.assertEqual(view['execution']['windows'][0]['timeouts'],1)
        self.assertEqual(view['analysis'],'complete')

    def test_unknown_error_generation_is_not_invented(self):
        self.save([dict(error=dict(operation='halt',code='lost'))])
        view=summary.build(self.path)
        self.assertEqual(view['analysis'],'partial')
        self.assertEqual(view['execution']['windows'],[])
        self.assertEqual(view['execution']['outcomes'],{'error':1})

    def test_missing_corrupt_and_audit_sources_are_partial(self):
        self.save();self.report['capture']={'status':'disabled'}
        report_data.write(self.path,self.report)
        self.assertIsNone(summary.build(self.path)['execution'])
        self.assertEqual(summary.build(self.path)['analysis'],'partial')
        self.save();(self.root/'records.json').write_text('{}')
        self.assertEqual(summary.build(self.path)['analysis'],'partial')
        self.report['report_audit_error_count']=1;self.save()
        self.assertIn('report_audit_error_count',summary.build(self.path)['issues'])

    def test_stale_and_tampered_summary_rejected(self):
        self.save();view=summary.write(self.path)
        view['collections']['checks']['total']=0
        (self.root/'summary.json').write_text(json.dumps(view))
        with self.assertRaises(ValueError):summary.read(self.path)
        summary.write(self.path)
        self.report['status']='FAIL';self.save()
        with self.assertRaises(ValueError):summary.read(self.path)

    def test_visible_limits_do_not_limit_counts(self):
        self.report['checks']=[dict(name=str(i),passed=True) for i in range(110)]
        self.report['checks'] += [dict(name='failed',passed=False)]*30
        self.save();view=summary.build(self.path)['collections']['checks']
        self.assertEqual((view['total'],view['failed'],view['groups_omitted']),(140,30,11))
        group=view['groups'][0]
        self.assertEqual(group['failed'],30)
        self.assertEqual(len(group['references']),20)
        self.assertEqual(group['failure_references_omitted'],10)

    def test_write_budget_removes_old_view_without_changing_source(self):
        self.save();summary.write(self.path);before=self.path.read_bytes()
        with patch.object(summary,'MAX_BYTES',1):
            with self.assertRaises(ValueError):summary.write(self.path)
        self.assertFalse((self.root/'summary.json').exists())
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(list(self.root.glob('.summary-*')),[])

    def test_failure_to_build_is_independent_of_verdict(self):
        self.save();self.report['report_policy']=dict(console='summary',representation='full')
        with patch.object(summary,'write',side_effect=OSError('disk unavailable')):
            output=write_reports(self.root,self.report)
        stored=report_data.read(self.path)
        self.assertEqual(stored['status'],'PASS')
        self.assertEqual(stored['command_code'],2)
        self.assertEqual(output['analysis'],'unavailable')
        self.assertIn('summary_error',stored)
        self.assertIn('infrastructure',(self.root/'junit.xml').read_text())

    def test_summary_junit_and_policy_transport(self):
        from test_session_config import SessionConfigTests
        from stm32_gdbtest.config_transport import dumps,loads
        fixture=SessionConfigTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        fixture.write('api.toml','schema=2\n[report]\nconsole="summary"')
        config=fixture.load('target="target.toml"\napi="api.toml"')
        self.assertEqual(loads(dumps(config)).config['api']['report']['console'],'summary')
        self.save();self.report['report_policy']=dict(console='summary',representation='compact')
        view=write_reports(self.root,self.report)
        self.assertEqual(view,summary.read(self.path))
        self.assertIn('derived',(self.root/'junit.xml').read_text())

    def test_corrupt_result_never_reuses_old_summary(self):
        self.save();summary.write(self.path)
        self.path.write_text('{"report_schema":999}')
        with self.assertRaises(ValueError):summary.write(self.path)
        self.assertFalse((self.root/'summary.json').exists())

    def test_fresh_process_import_orders(self):
        import subprocess
        import sys
        for modules in [('reports','report_summary'),('result_capture','runner')]:
            program='; '.join('import stm32_gdbtest.'+name for name in modules)
            result=subprocess.run([sys.executable,'-c',program],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)

    def test_missing_checks_and_invalid_outcomes_are_not_success(self):
        self.save();self.report.pop('checks');report_data.write(self.path,self.report)
        self.assertEqual(summary.build(self.path)['analysis'],'partial')
        self.report['checks']=[dict(name='wrong',passed=1)]
        self.save();view=summary.build(self.path)
        self.assertEqual(view['collections']['checks']['unclassified'],1)
        self.assertEqual(view['analysis'],'partial')

    def test_user_measurements_are_not_averaged(self):
        self.save()
        data=json.loads((self.root/'records.json').read_bytes())
        data['records']=[dict(sequence=1,name='temperature',data=[2,100,3])]
        raw=json.dumps(data).encode();(self.root/'records.json').write_bytes(raw)
        self.report['capture'].update(count=1,sha256=hashlib.sha256(raw).hexdigest())
        report_data.write(self.path,self.report)
        self.assertEqual(summary.build(self.path)['execution']['total'],0)
        self.assertNotIn('average',json.dumps(summary.build(self.path)))

    def test_json_types_are_not_interchangeable(self):
        self.save();view=summary.write(self.path)
        for key,value in [('schema',True),('derived',1)]:
            changed=copy.deepcopy(view);changed[key]=value
            (self.root/'summary.json').write_text(json.dumps(changed))
            with self.assertRaises(ValueError):summary.read(self.path)
        self.assertNotEqual(summary.label(None),summary.label('null'))

    def test_mutation_count_does_not_claim_success(self):
        self.report['mutations']=[dict(expression='counter',value=7,before=0,after=0)]
        self.save();view=summary.build(self.path)['collections']['mutations']
        self.assertEqual(view['total'],1)
        self.assertIsNone(view['failed'])
        self.assertIsNone(view['groups'][0]['failed'])

    def test_source_cannot_be_overwritten_by_output(self):
        self.save();other=self.root/'summary.json';other.write_bytes(self.path.read_bytes())
        before=other.read_bytes()
        with self.assertRaises(ValueError):summary.write(other)
        self.assertEqual(other.read_bytes(),before)

    def test_arbitrary_json_is_not_a_result(self):
        self.path.write_text('{}')
        with self.assertRaises(ValueError):summary.build(self.path)
