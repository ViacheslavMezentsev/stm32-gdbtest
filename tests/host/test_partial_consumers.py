"""A3.3: incomplete sources cannot become ordinary exports or green DDTT marks."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from stm32_gdbtest import evidence, report_data, result_capture, result_export, result_index, result_report, report_summary
from stm32_gdbtest.records import Journal
from stm32_gdbtest.results import Limits
import test_ddtt_coverage as fixture

class ConsumerTests(unittest.TestCase):
    def test_full_compact_policies_preserve_verdict_and_block_projection(self):
        for representation in ('full','compact'):
            for policy in ('journal','report','both'):
                for verdict in ('PASS','FAIL'):
                    with self.subTest(representation=representation,policy=policy,verdict=verdict):
                        f=fixture.DdttCoverageTests();f.setUp()
                        try:
                            data=copy.deepcopy(f.result);data['status']=verdict;data['duration_s']=0
                            report_data.configure(data,dict(schema=3,
                                report=dict(representation=representation,on_limit='truncate' if policy!='journal' else 'error',max_rows_per_collection=1),
                                journal=dict(on_limit='truncate' if policy!='report' else 'error')))
                            j=Journal(max_records=1);j.on_limit='truncate' if policy!='report' else 'error'
                            evidence.journal(data,j.record,'sample',1)
                            if policy!='report':evidence.journal(data,j.record,'sample',2)
                            if policy!='journal':report_data.append(data,'checks',dict(name='late',passed=verdict!='FAIL'))
                            path=f.root/'runs/run1/result.json';path.parent.mkdir(parents=True)
                            result_capture.save(path.parent,data,SimpleNamespace(_journal=j),'normal')
                            result_capture.finalize(path.parent,data,True)
                            report_data.write(path,data)
                            original=path.read_bytes()
                            bundle=result_export.export([path],f.root/'export')
                            self.assertEqual(bundle['command_code'],2)
                            self.assertEqual(bundle['records'],[])
                            self.assertEqual(bundle['measurements'],[])
                            self.assertIn('incomplete evidence',bundle['diagnostics'][0]['message'])
                            selection=dict(schema=1,campaign_id='C',name='Partial',runs=[dict(result='runs/run1/result.json',stand='lab')])
                            index=result_index.build(f.root,selection)
                            self.assertEqual(index['runs'][0]['verdict'],verdict)
                            self.assertEqual(index['command_code'],2)
                            self.assertEqual(result_report.report(f.root,index,f.root/'html',Limits()),2)
                            self.assertIn('Incomplete evidence',(f.root/'html/campaign.html').read_text(encoding='utf-8'))
                            rows=f.run_export(path)
                            self.assertEqual(rows[0]['state'],'UNKNOWN')
                            self.assertNotIn('DA:',(f.out/'lcov.info').read_text())
                            view=report_summary.write(path)
                            self.assertEqual(report_summary.read(path),view)
                            self.assertEqual(view['analysis'],'partial')
                            if policy!='journal':self.assertEqual(view['collections']['checks']['availability'],'truncated')
                            self.assertEqual(path.read_bytes(),original)
                            report_data.close(data)
                        finally:f.doCleanups()

    def test_complete_source_still_exports_and_confirms(self):
        f=fixture.DdttCoverageTests();f.setUp()
        try:
            data=f.result;report_data.configure(data,{})
            j=Journal();evidence.journal(data,j.record,'sample',1)
            path=f.root/'run/result.json';path.parent.mkdir()
            result_capture.save(path.parent,data,SimpleNamespace(_journal=j),'normal')
            result_capture.finalize(path.parent,data,True);report_data.write(path,data)
            bundle=result_export.export([path],f.root/'export')
            self.assertEqual(bundle['command_code'],0)
            self.assertEqual(len(bundle['records']),1)
            self.assertEqual(f.run_export(path)[0]['state'],'CONFIRMED')
        finally:f.doCleanups()
