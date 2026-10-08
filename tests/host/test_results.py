"""Offline result export, bounded I/O and publication contracts (ТЗ 5.22)."""
import copy
import csv
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
from unittest.mock import patch

from stm32_gdbtest import results as m
from stm32_gdbtest.result_files import Budget, ownership
from stm32_gdbtest import result_export as export_tools

def save(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')


class PipelineTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.inputs = self.root / 'evidence'
        self.inputs.mkdir()
        raw = json.dumps(dict(schema=1, run_id='one', case_id='C', records=[dict(sequence=1, name='event', data={'value': 0, 'flag': False})])).encode()
        (self.inputs / 'records.json').write_bytes(raw)
        save(self.inputs / 'result.json', dict(id='C', run_id='one', status='FAIL', mode='hardware', command_code=1,
                  capture=dict(status='saved', completion='interrupted', path='records.json', count=1,
                               sha256=hashlib.sha256(raw).hexdigest())))
        self.selection = dict(schema=1, campaign_id='campaign', name='Fixture', runs=[dict(result='result.json', stand='label')])
        self.output = self.root / 'output'

    def test_combined_roundtrip(self):
        self.assertEqual(m.pipeline(self.inputs, self.selection, self.output), 0)
        index, _ = m.indexer.load(self.output / 'index.json')
        export, _ = m.indexer.load(self.output / 'export.json')
        self.assertEqual(export['records'][0]['data'], {'value': 0, 'flag': False})
        self.assertEqual(index['runs'][0]['verdict'], 'FAIL')
        self.assertEqual(m.check(self.inputs, index)['command_code'], 0)
        with self.assertRaises(FileExistsError):
            m.pipeline(self.inputs, self.selection, self.output)

    def test_limits_no_publication(self):
        for limits in (m.Limits(files=1), m.Limits(input_bytes=1), m.Limits(output_bytes=1)):
            with self.assertRaises(ValueError):
                m.pipeline(self.inputs, self.selection, self.output, limits=limits)
            self.assertFalse(self.output.exists())
            self.assertFalse(list(self.root.glob('.results-*')))
        with self.assertRaises(ValueError):
            m.Limits(runs=True)

    def test_source_mutation_no_publication(self):
        original = m.Snapshot.unchanged
        def changed(snapshot):
            (self.inputs / 'records.json').write_text('changed')
            original(snapshot)
        with patch.object(m.Snapshot, 'unchanged', changed), self.assertRaisesRegex(ValueError, 'source changed'):
            m.pipeline(self.inputs, self.selection, self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.results-*')))

    def test_write_failure_no_publication(self):
        with patch.object(m, 'write_json', side_effect=OSError('disk refusal')), self.assertRaises(OSError):
            m.pipeline(self.inputs, self.selection, self.output)
        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob('.results-*')))

    def test_imported_index_validation(self):
        m.pipeline(self.inputs, self.selection, self.output)
        index, _ = m.indexer.load(self.output / 'index.json')
        mutations = [lambda i: i.update(schema=True), lambda i: i.update(unexpected=0),
                     lambda i: i.update(runs={}), lambda i: i['runs'][0].update(command_code=True),
                     lambda i: i['runs'][0]['artifacts'][0].update(path='../escape'),
                     lambda i: i['runs'][0]['artifacts'][0].update(size=True),
                     lambda i: i['runs'][0]['artifacts'][0].update(sha256='bad'),
                     lambda i: i['runs'][0]['artifacts'][0].update(state='ok'),
                     lambda i: i['runs'].append(copy.deepcopy(i['runs'][0]))]
        for mutation in mutations:
            bad = copy.deepcopy(index)
            mutation(bad)
            with self.assertRaises(ValueError):
                m.check(self.inputs, bad)

    def test_prepare_and_bad_source(self):
        save(self.inputs / 'prepare.json', dict(id='PREP', status='PASS', mode='prepare'))
        (self.inputs / 'bad.json').write_text('{invalid')
        self.selection['runs'].extend([dict(result='prepare.json', stand='label', assigned_id='legacy'),
                                       dict(result='bad.json', stand='label')])
        self.assertEqual(m.pipeline(self.inputs, self.selection, self.output), 2)
        export, _ = m.indexer.load(self.output / 'export.json')
        self.assertEqual(len(export['records']), 1)
        self.assertEqual(export['selection_indices'], [0, 2])
        index, _ = m.indexer.load(self.output / 'index.json')
        self.assertEqual(index['runs'][1]['identity_source'], 'assigned')

    def test_generic_and_projection_types(self):
        values = [None, False, 0, 2 ** 200, '=1+1', 'Привет', {'a.b': [1, None]}]
        records = [dict(sequence=i + 1, name='event', data=value) for i, value in enumerate(values)]
        raw = json.dumps(dict(schema=1, run_id='one', case_id='C', records=records)).encode()
        (self.inputs / 'records.json').write_bytes(raw)
        report, _ = m.indexer.load(self.inputs / 'result.json')
        report['capture'].update(count=len(records), sha256=hashlib.sha256(raw).hexdigest())
        save(self.inputs / 'result.json', report)
        self.assertEqual(m.pipeline(self.inputs, self.selection, self.output), 0)
        with (self.output / 'records.csv').open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([json.loads(row['data_json']) for row in rows], values)
        self.assertIs(type(json.loads(rows[1]['data_json'])), bool)
        self.assertIs(type(json.loads(rows[2]['data_json'])), int)
        spec = dict(name='v', record='event', path=['v'], unit='V')
        for data, state in [({}, 'missing'), ({'v': None}, 'null'), ({'v': False}, 'value'), ([], 'error')]:
            self.assertEqual(export_tools.project(dict(sequence=1, name='event', data=data), spec)['state'], state)
        self.assertEqual(export_tools.project(dict(sequence=1, name='event', data={'v': False}),
                                             dict(spec, scale=1))['state'], 'error')
        row = export_tools.project(dict(sequence=1, name='event', data={'a.b': {'v': 3300}}),
                                   dict(spec, path=['a.b', 'v'], scale=0.001))
        self.assertAlmostEqual(row['value'], 3.3)

    def test_run_series_and_exact_io_boundaries(self):
        expanded = dict(self.selection, runs=self.selection['runs'] * 2)
        with self.assertRaisesRegex(ValueError, 'run limit'):
            m.pipeline(self.inputs, expanded, self.output, limits=m.Limits(runs=1))
        config = self.root / 'export.toml'
        config.write_text('schema=1\n[[series]]\nname="a"\nrecord="event"\npath=["value"]\nunit="V"\n'
                          '[[series]]\nname="b"\nrecord="event"\npath=["flag"]\nunit="bool"\n')
        with self.assertRaisesRegex(ValueError, 'series count'):
            m.pipeline(self.inputs, self.selection, self.output, config, m.Limits(series=1))
        exact = sum(p.stat().st_size for p in self.inputs.iterdir())
        with self.assertRaisesRegex(ValueError, 'input size'):
            m.pipeline(self.inputs, self.selection, self.output, limits=m.Limits(input_bytes=exact - 1))
        self.assertEqual(m.pipeline(self.inputs, self.selection, self.output, config, m.Limits(input_bytes=exact)), 0)
        index, _ = m.indexer.load(self.output / 'index.json')
        self.assertEqual(m.check(self.inputs, index, m.Limits(input_bytes=exact))['command_code'], 0)
        with self.assertRaisesRegex(ValueError, 'verification input size'):
            m.check(self.inputs, index, m.Limits(input_bytes=exact - 1))

    def test_verification_publication_and_exact_output_limit(self):
        m.pipeline(self.inputs, self.selection, self.output)
        index, _ = m.indexer.load(self.output / 'index.json')
        path = self.root / 'verify.json'
        self.assertEqual(m.verify_to_file(self.inputs, index, path), 0)
        exact = path.stat().st_size
        self.assertEqual(m.verify_to_file(self.inputs, index, self.root / 'exact.json', m.Limits(output_bytes=exact)), 0)
        absent = self.root / 'small.json'
        with self.assertRaisesRegex(ValueError, 'output size'):
            m.verify_to_file(self.inputs, index, absent, m.Limits(output_bytes=exact - 1))
        self.assertFalse(absent.exists())
        with patch('stm32_gdbtest.result_files.os.link', side_effect=OSError('publication refused')), self.assertRaises(OSError):
            m.verify_to_file(self.inputs, index, absent)
        self.assertFalse(absent.exists())
        with self.assertRaises(FileExistsError):
            m.verify_to_file(self.inputs, index, path)
        self.assertFalse(list(self.root.glob('.results-*')))
        self.assertFalse(list(self.root.glob('*.lock')))

    def test_output_ownership(self):
        with ownership(self.output):
            with self.assertRaises(FileExistsError):
                m.pipeline(self.inputs, self.selection, self.output)
            self.assertTrue(self.output.with_name('output.lock').exists())
        self.assertFalse(self.output.with_name('output.lock').exists())

    def test_missing_changed_and_duplicate_identity(self):
        m.pipeline(self.inputs, self.selection, self.output)
        index, _ = m.indexer.load(self.output / 'index.json')
        (self.inputs / 'records.json').write_text('{}')
        self.assertEqual(m.check(self.inputs, index)['artifacts'][1]['state'], 'changed')
        (self.inputs / 'records.json').unlink()
        self.assertEqual(m.check(self.inputs, index)['artifacts'][1]['state'], 'missing')
        self.assertEqual(index['runs'][0]['verdict'], 'FAIL')
        duplicated = dict(self.selection, runs=self.selection['runs'] * 2)
        with self.assertRaisesRegex(ValueError, 'duplicate run_id'):
            m.pipeline(self.inputs, duplicated, self.root / 'duplicate')

    def test_invalid_configuration_and_paths(self):
        config = self.root / 'export.toml'
        base = 'schema=1\n[[series]]\nname="v"\nrecord="event"\npath=[]\nunit="V"\n'
        for text in [base + 'scale=true', base + 'offset=nan', base + 'unknown=1']:
            config.write_text(text)
            with self.assertRaises(ValueError):
                m.pipeline(self.inputs, self.selection, self.output, config)
        for path in ['../escape', '/absolute', 'C:/absolute', 'a\\b']:
            invalid = dict(self.selection, runs=[dict(result=path, stand='label')])
            with self.assertRaises(ValueError):
                m.pipeline(self.inputs, invalid, self.output)

    def test_cli_without_gdb(self):
        selection = self.root / 'selection.json'
        save(selection, self.selection)
        def cli(*args):
            return subprocess.run([sys.executable, '-m', 'stm32_gdbtest', 'results', *args],
                                  capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=30)
        result = cli('export', '--root', str(self.inputs), '--selection', str(selection), '--output', str(self.output))
        self.assertEqual(result.returncode, 0, result.stderr)
        result = cli('verify', '--root', str(self.inputs), '--index', str(self.output / 'index.json'),
                     '--output', str(self.root / 'verification.json'))
        self.assertEqual(result.returncode, 0, result.stderr)
        result = cli('export', '--root', str(self.inputs), '--selection', str(selection), '--output', str(self.output))
        self.assertEqual(result.returncode, 2)

    def test_symlink_refused(self):
        try:
            (self.inputs / 'alias').symlink_to(self.inputs / 'result.json')
        except OSError as exc:
            self.skipTest(str(exc))
        invalid = dict(self.selection, runs=[dict(result='alias', stand='label')])
        with self.assertRaisesRegex(ValueError, 'symlink'):
            m.pipeline(self.inputs, invalid, self.output)
