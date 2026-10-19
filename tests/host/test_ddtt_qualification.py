"""Applicability never converts a raw PASS into qualified evidence without facts."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from tools import ddtt_coverage as coverage, ddtt_qualification as qualification

spec = importlib.util.spec_from_file_location('qualification_example', Path(__file__).resolve().parents[2]/'examples/ddtt-qualification/run.py')
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


class QualificationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.mapping, self.result, self.snapshot = example.fixture(self.root)
        self.path = self.root/'result.json'
        self.out = self.root/'view'

    def run_case(self, bind=True):
        self.path.write_text(json.dumps(self.result), encoding='utf-8')
        admission = self.path.with_name('admission.json')
        if admission.exists(): admission.unlink()
        if bind: qualification.bind(self.path, self.snapshot)
        before = self.path.read_bytes()
        rows = coverage.export(self.root, self.mapping, [self.path], self.out)
        self.assertEqual(before, self.path.read_bytes())
        return rows

    def test_nominal_and_independent(self):
        rows = self.run_case()
        self.assertEqual([p['state'] for p in rows], ['CONFIRMED','CONFIRMED'])
        self.assertTrue(coverage.load(self.out/'ddtt-evidence.json')['acceptance']['accepted'])

    def test_changed_nominal_keeps_result_and_measurement(self):
        self.snapshot['measurements'][0].update(value=25001560.17, uncertainty=13575.13)
        self.mapping['qualification']['conditions']['clock'].update(min=24750000, max=25250000)
        rows = self.run_case()
        self.assertEqual([r['state'] for r in rows], ['CONFIRMED', 'CONFIRMED'])
        original = self.path.read_bytes()
        admission = self.path.with_name('admission.json').read_bytes()
        self.mapping['qualification']['conditions']['clock'].update(min=15840000, max=16160000)
        rows = coverage.export(self.root, self.mapping, [self.path], self.out)
        self.assertEqual((rows[0]['raw_state'], rows[0]['state'], rows[0]['applicability']['status']),
                         ('CONFIRMED', 'UNKNOWN', 'VIOLATED'))
        self.assertEqual(rows[1]['state'], 'CONFIRMED')
        self.assertEqual(original, self.path.read_bytes())
        self.assertEqual(admission, self.path.with_name('admission.json').read_bytes())
        self.assertNotIn('DA:5,', (self.out/'lcov.info').read_text())

    def test_wrong_clock_pass_not_accepted(self):
        self.snapshot['measurements'][0]['value'] = 16000000
        row = self.run_case()[0]
        self.assertEqual((row['raw_state'],row['state'],row['applicability']['status']), ('CONFIRMED','UNKNOWN','VIOLATED'))
        self.assertFalse(coverage.load(self.out/'ddtt-evidence.json')['acceptance']['accepted'])
        self.assertNotIn('DA:5,', (self.out/'lcov.info').read_text())

    def test_failed_check_without_admission_not_zero(self):
        self.result['status']='FAIL';self.result['checks'][0]['passed']=False
        row = self.run_case(False)[0]
        self.assertEqual((row['raw_state'],row['state']), ('FAILED','UNKNOWN'))
        self.assertNotIn('DA:5,0',(self.out/'lcov.info').read_text())

    def test_valid_fail_red(self):
        self.result['status']='FAIL';self.result['checks'][0]['passed']=False
        self.assertEqual(self.run_case()[0]['state'],'FAILED')

    def test_missing_future_stale_invalidated_conflicting(self):
        original=copy.deepcopy(self.snapshot)
        for edit in ('missing','future','stale','expired_during','invalidated','duplicate','declared','uncertain','units'):
            with self.subTest(edit=edit):
                self.snapshot=copy.deepcopy(original);m=self.snapshot['measurements'][0]
                if edit=='missing':self.snapshot['measurements']=[]
                if edit=='future':m['observed_utc']='2026-10-19T00:00:11Z'
                if edit=='stale':m['valid_until']='2026-10-19T00:00:01Z'
                if edit=='expired_during':m['valid_until']='2026-10-19T00:00:11Z'
                if edit=='invalidated':m['invalidated_utc']='2026-10-19T00:00:11Z'
                if edit=='duplicate':self.snapshot['measurements'].append(copy.deepcopy(m))
                if edit=='declared':m['method']='declared'
                if edit=='uncertain':m['uncertainty']=200000
                if edit=='units':m['unit']='MHz'
                self.assertEqual(self.run_case()[0]['state'],'UNKNOWN')

    def test_context_mismatches(self):
        original=copy.deepcopy(self.snapshot)
        for key in ('instance','inputs_sha256','elf_sha256','environment'):
            self.snapshot=copy.deepcopy(original);self.snapshot['context'][key]='other'
            self.assertEqual(self.run_case()[0]['applicability']['reason'],'context_mismatch')

    def test_duration_missing_and_invalid(self):
        for duration in (None,-1,True,float('inf')):
            self.result['duration_s']=duration
            self.assertEqual(self.run_case()[0]['state'],'UNKNOWN')

    def test_raw_error_stays_unknown(self):
        self.result['status']='ERROR'
        self.assertEqual(self.run_case()[0]['state'],'UNKNOWN')

    def test_malformed_policy_fails_export_and_clears(self):
        self.run_case()
        self.mapping['points'][0]['requires']=['typo']
        with self.assertRaises(ValueError):coverage.export(self.root,self.mapping,[self.path],self.out)
        self.assertEqual((self.out/'lcov.info').read_text(),'')

    def test_legacy_cannot_silently_ignore_qualification(self):
        self.mapping['schema']=1
        with self.assertRaises(ValueError):self.run_case()

    def test_malformed_admission(self):
        self.run_case()
        for text in ('null','[]','{"schema":1}', '{invalid'):
            self.path.with_name('admission.json').write_text(text)
            rows=coverage.export(self.root,self.mapping,[self.path],self.out)
            self.assertEqual(rows[0]['state'],'UNKNOWN')

    def test_tamper_snapshot_or_result_binding(self):
        self.run_case()
        a=coverage.load(self.path.with_name('admission.json'))
        for key in ('snapshot_sha256','result_sha256'):
            changed=copy.deepcopy(a);changed[key]='0'*64
            self.path.with_name('admission.json').write_text(json.dumps(changed))
            self.assertEqual(coverage.project(self.root,self.mapping,[self.path])[0]['state'],'UNKNOWN')

    def test_bind_does_not_overwrite(self):
        self.run_case()
        with self.assertRaises(FileExistsError):qualification.bind(self.path,self.snapshot)

    def test_latest_missing_does_not_reuse_old(self):
        self.run_case()
        folder=self.root/'new';folder.mkdir();path=folder/'result.json'
        path.write_text(json.dumps(dict(self.result,started_utc='2026-10-19T00:00:20Z')))
        rows=coverage.project(self.root,self.mapping,[self.path,path])
        self.assertEqual(rows[0]['state'],'UNKNOWN')

    def test_optional_capability_absent(self):
        self.mapping['points'][0]['required']=False
        self.mapping['qualification']['conditions']['clock']=dict(kind='capability',unit='present',min=1,max=1,max_age_s=60)
        self.snapshot['measurements'][0].update(value=0,uncertainty=0,unit='present')
        rows=self.run_case()
        self.assertEqual(rows[0]['applicability']['status'],'NOT_APPLICABLE')
        self.assertTrue(coverage.load(self.out/'ddtt-evidence.json')['acceptance']['accepted'])

    def test_required_capability_absent_blocks(self):
        self.mapping['qualification']['conditions']['clock']=dict(kind='capability',unit='present',min=1,max=1,max_age_s=60)
        self.snapshot['measurements'][0].update(value=0,uncertainty=0,unit='present')
        self.assertEqual(self.run_case()[0]['applicability']['status'],'VIOLATED')

    def test_empty_required_set_not_accepted(self):
        for p in self.mapping['points']:p['required']=False
        self.run_case()
        self.assertFalse(coverage.load(self.out/'ddtt-evidence.json')['acceptance']['accepted'])

    def test_model_demo(self):
        self.assertEqual(len(example.demo(self.root/'demo')),10)


if __name__=='__main__':unittest.main()
