import importlib.util
import json
from pathlib import Path
import tempfile
import tomllib
import unittest
from tools import ddtt_qualification as q

BASE = Path(__file__).resolve().parents[2]/'examples/ddtt-qualification'
spec = importlib.util.spec_from_file_location('qualification_data', BASE/'snapshot_data.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class SnapshotDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.snapshot = {'schema': 1, 'context': {'instance': 'плата'}, 'measurements': [{'invalidated_utc': None}]}
        self.data = self.root/'qualification.toml'
        self.sha = bridge.write_data(self.data, self.snapshot)
        self.result = self.root/'result.json'
        self.result.write_text(json.dumps(dict(run_id='run-1', id='CASE', status='PASS', capture={'status': 'saved'})))
        self.record = dict(snapshot=self.snapshot, snapshot_sha256=q.digest(q.canonical(self.snapshot)), data_sha256=self.sha)
        self.records = dict(schema=1, run_id='run-1', case_id='CASE', records=[dict(name='qualification_input', data=self.record)])

    def save(self):
        (self.root/'records.json').write_text(json.dumps(self.records))

    def test_roundtrip_null_unicode_and_hash(self):
        data = tomllib.loads(self.data.read_text())
        self.assertEqual(json.loads(data['snapshot_json']), self.snapshot)
        self.assertEqual(data['snapshot_sha256'], self.record['snapshot_sha256'])
        with self.assertRaises(FileExistsError):
            bridge.write_data(self.data, self.snapshot)

    def test_pass_and_fail_remain_unchanged(self):
        for status in ('PASS', 'FAIL'):
            self.result.write_text(json.dumps(dict(run_id='run-1', id='CASE', status=status, capture={'status': 'saved'})))
            self.save()
            original = self.result.read_bytes()
            bridge.verify_records(self.result, self.snapshot, self.sha)
            self.assertEqual(original, self.result.read_bytes())

    def test_missing_duplicate_or_wrong_record(self):
        for rows in ([], self.records['records']*2, [dict(name='other', data=self.record)]):
            self.records['records'] = rows
            self.save()
            with self.assertRaises(ValueError):
                bridge.verify_records(self.result, self.snapshot, self.sha)

    def test_foreign_identity_and_capture(self):
        for key in ('run_id', 'case_id'):
            old = self.records[key]
            self.records[key] = 'foreign'
            self.save()
            with self.assertRaises(ValueError):
                bridge.verify_records(self.result, self.snapshot, self.sha)
            self.records[key] = old
        self.result.write_text(json.dumps(dict(run_id='run-1', id='CASE', capture={'status': 'unavailable'})))
        self.save()
        with self.assertRaises(ValueError):
            bridge.verify_records(self.result, self.snapshot, self.sha)

    def test_hash_or_payload_mismatch(self):
        for key, value in [('data_sha256', '0'*64), ('snapshot_sha256', '0'*64), ('snapshot', {})]:
            old = self.record[key]
            self.record[key] = value
            self.save()
            with self.assertRaises(ValueError):
                bridge.verify_records(self.result, self.snapshot, self.sha)
            self.record[key] = old

    def test_missing_records(self):
        with self.assertRaises(FileNotFoundError):
            bridge.verify_records(self.result, self.snapshot, self.sha)


if __name__ == '__main__':
    unittest.main()
