"""DDTT projection contract, without GDB or a board (TC-172)."""
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

from tools import ddtt_coverage as coverage


class DdttCoverageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        (self.root / 'app.cpp').write_text('void step() {\n  ++count;\n}\n', encoding='utf-8')
        self.point = dict(source='app.cpp', source_sha256=coverage.digest(self.root / 'app.cpp'),
                          anchor='++count;', scenario='ONE', check='count advanced')
        self.mapping = dict(schema=1, elf_sha256='a' * 64, points=[self.point])
        self.result = dict(mode='hardware', id='ONE', run_id='run1', status='PASS',
                           started_utc='2026-10-15T00:00:00Z', elf_sha256='a' * 64,
                           build_manifest={'inputs': [{'file': 'app.cpp', 'sha256': self.point['source_sha256']}]},
                           checks=[{'name': 'count advanced', 'passed': True}])
        self.out = self.root / 'out'

    def save(self, data, name='run1'):
        path = self.root / 'runs' / name / 'result.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding='utf-8')
        return path

    def run_export(self, *results):
        return coverage.export(self.root, self.mapping, results, self.out)

    def test_confirmed_source_line_and_sidecar(self):
        rows = self.run_export(self.save(self.result))
        self.assertEqual((rows[0]['line'], rows[0]['state']), (2, 'CONFIRMED'))
        self.assertIn('DA:2,1', (self.out / 'lcov.info').read_text())
        self.assertEqual(coverage.load(self.out / 'ddtt-evidence.json')['summary'], {'CONFIRMED': 1})

    def test_strict_evidence_loss_blocks_confirmation(self):
        from stm32_gdbtest import evidence
        from stm32_gdbtest.records import Journal, RecordError
        evidence.initialize(self.result)
        journal = Journal(max_records=1)
        evidence.journal(self.result, journal.record, 'sample', 1)
        with self.assertRaises(RecordError):
            evidence.journal(self.result, journal.record, 'sample', 2)
        rows = self.run_export(self.save(self.result))
        self.assertEqual(rows[0]['state'], 'UNKNOWN')
        self.assertEqual(rows[0]['reason'], 'report evidence unavailable')
        self.assertNotIn('DA:', (self.out / 'lcov.info').read_text())

    def test_failed_check_is_zero(self):
        self.result['status'] = 'FAIL'
        self.result['checks'][0]['passed'] = False
        self.run_export(self.save(self.result))
        self.assertIn('DA:2,0', (self.out / 'lcov.info').read_text())

    def test_unknown_cases_are_not_zero(self):
        for change in ({'mode': 'prepare'}, {'status': 'ERROR'}, {'status': 'SKIP'},
                       {'checks': []}, {'elf_sha256': 'b' * 64}, {'build_manifest': {}},
                       {'checks': [{'name': 'count advanced', 'passed': 1}]}):
            with self.subTest(change=change):
                data = dict(self.result, **change)
                self.assertEqual(self.run_export(self.save(data))[0]['state'], 'UNKNOWN')
                self.assertNotIn('DA:', (self.out / 'lcov.info').read_text())

    def test_latest_error_or_different_elf_does_not_reuse_old_green(self):
        old = self.save(self.result)
        for change in ({'status': 'ERROR'}, {'elf_sha256': 'b' * 64}):
            new = dict(self.result, started_utc='2026-10-16T00:00:00Z', **change)
            self.assertEqual(self.run_export(old, self.save(new, 'run2'))[0]['state'], 'UNKNOWN')

    def test_equal_timestamps_are_ambiguous(self):
        rows = self.run_export(self.save(self.result), self.save(self.result, 'run2'))
        self.assertEqual(rows[0]['reason'], 'ambiguous latest attempt')

    def test_timezone_order(self):
        old = self.save(self.result)
        new = dict(self.result, started_utc='2026-10-15T02:00:00+01:00', status='ERROR')
        self.assertEqual(self.run_export(old, self.save(new, 'run2'))[0]['state'], 'UNKNOWN')

    def test_repeated_check_and_same_line_fail_wins(self):
        self.result['checks'].append({'name': 'count advanced', 'passed': False})
        self.assertEqual(self.run_export(self.save(self.result))[0]['state'], 'FAILED')
        rows = [dict(absolute_source='x', line=2, state=s) for s in ('CONFIRMED', 'FAILED', 'UNKNOWN')]
        self.assertIn('DA:2,0', coverage.render(rows))

    def test_source_change_clears_old_marks(self):
        path = self.save(self.result)
        self.run_export(path)
        (self.root / 'app.cpp').write_text('changed')
        with self.assertRaises(ValueError):
            self.run_export(path)
        self.assertEqual((self.out / 'lcov.info').read_text(), '')
        self.assertEqual(coverage.load(self.out / 'ddtt-evidence.json')['status'], 'ERROR')

    def test_duplicate_anchor_and_escape_rejected(self):
        for source, anchor in (('../outside.cpp', '++count;'), ('app.cpp', 'missing')):
            self.point.update(source=source, anchor=anchor)
            with self.assertRaises((ValueError, OSError)):
                self.run_export()

    def test_duplicate_anchor_rejected(self):
        source = self.root / 'app.cpp'
        source.write_text('++count;\n++count;\n', encoding='utf-8')
        self.point['source_sha256'] = coverage.digest(source)
        with self.assertRaises(ValueError):
            self.run_export()

    def test_bind_example_then_export(self):
        template = self.root / 'template.json'
        template.write_text(json.dumps({'schema': 1, 'points': [self.point]}), encoding='utf-8')
        elf = self.root / 'firmware.elf'
        elf.write_bytes(b'host fixture, not firmware')
        bound = self.root / 'map.json'
        script = Path(__file__).resolve().parents[2] / 'examples/ddtt-coverage/bind_map.py'
        subprocess.run([sys.executable, str(script), '--project', str(self.root), '--elf', str(elf),
                        '--template', str(template), '--out', str(bound)], check=True, capture_output=True)
        self.mapping = coverage.load(bound)
        self.result['elf_sha256'] = coverage.digest(elf)
        self.assertEqual(self.run_export(self.save(self.result))[0]['state'], 'CONFIRMED')

    def test_empty_campaign(self):
        self.assertEqual(self.run_export()[0]['state'], 'UNKNOWN')

    def test_cli_error_invalidates_previous_output(self):
        self.run_export(self.save(self.result))
        bad = self.root / 'bad.json'
        bad.write_text('{')
        code = coverage.main(['--project', str(self.root), '--map', str(bad),
                              '--runs', str(self.root / 'runs'), '--out', str(self.out)])
        self.assertEqual(code, 2)
        self.assertEqual((self.out / 'lcov.info').read_text(), '')

    def test_manifest_duplicate_is_unknown(self):
        self.result['build_manifest']['inputs'] *= 2
        self.assertEqual(self.run_export(self.save(self.result))[0]['state'], 'UNKNOWN')

    def test_bad_schema_and_hash_rejected(self):
        for field, value in (('schema', 2), ('elf_sha256', 'placeholder')):
            mapping = dict(self.mapping, **{field: value})
            with self.assertRaises(ValueError):
                coverage.project(self.root, mapping, [])


if __name__ == '__main__':
    unittest.main()
