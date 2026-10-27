"""A2.1 lossless encoding, budgets, malformed references and capture compatibility."""
import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from stm32_gdbtest.compact_records import CompactJournal, decode
from stm32_gdbtest.records import Journal, RecordError
from stm32_gdbtest.configuration import MAXIMUMS_V2, DEFAULTS_V2, load_session
from stm32_gdbtest.mmio import MMIO, Register
from stm32_gdbtest.result_capture import save, read, finalize
from stm32_gdbtest.config_transport import dumps, loads
from test_session_config import TARGET


def exercise(journal, n=4):
    reg = Register('P.R', 0x40000000, 32, 'read-write')
    transport = SimpleNamespace(prepare=lambda: None, write=lambda *args: None)
    m = MMIO(SimpleNamespace(registers={'P.R': reg}, sha256='a'*64), transport, journal.mmio_record)
    journal.record('mmio.attempt', {'user': [1, 2]})
    for i in range(n):
        m.write('P.R', i, reason='restore')
        journal.record('measurement', i)
    return journal


class Tests(unittest.TestCase):
    def test_lossless_and_detached(self):
        full = exercise(Journal(**MAXIMUMS_V2))
        compact = exercise(CompactJournal(**MAXIMUMS_V2))
        self.assertEqual(compact.records(), full.records())
        self.assertEqual(len(compact.definitions), 1)
        self.assertLess(compact._nodes, full._nodes)
        rows = compact.records(); rows[1]['data']['original']['address'] = 0
        self.assertEqual(compact.records(), full.records())
        decoded = decode(json.loads(json.dumps(compact.payload('run', 'case'))))
        self.assertEqual(decoded.records(), full.records())
        self.assertEqual(decoded.records('measurement'), full.records('measurement'))

    def test_atomic_definition_failure(self):
        j = CompactJournal(max_nodes=5)
        with self.assertRaises(RecordError): exercise(j)
        self.assertEqual(j.definitions, {})
        self.assertEqual(j._nodes, 0)
        self.assertEqual(j._entries, [])

    def test_capture_and_stream_reader(self):
        j = exercise(CompactJournal(**MAXIMUMS_V2))
        with tempfile.TemporaryDirectory() as folder:
            report = dict(run_id='run', id='case', status='PASS')
            target = SimpleNamespace(_journal=j)
            save(folder, report, target, 'normal'); finalize(folder, report, True)
            self.assertEqual(report['command_code'], 0)
            self.assertEqual(read(folder, report)['records'], j.records())
            self.assertEqual(list(read(folder, report, materialize=False)['records']), j.records())
            self.assertEqual(json.loads(Path(folder, 'records.json').read_text())['schema'], 2)

    def test_corrupt_refs_and_pairs(self):
        payload = exercise(CompactJournal(**MAXIMUMS_V2)).payload('r', 'c')
        mutations = [lambda p: p['records'][1]['data'].update(definition='missing'),
                     lambda p: p['records'][2]['data'].update(operation_id=999),
                     lambda p: p['records'][2].update(sequence=9),
                     lambda p: p['records'][2]['data']['payload'].update(status='PASS'),
                     lambda p: p['records'][1]['data']['payload'].pop('reason'),
                     lambda p: p['records'][1]['data']['payload'].update(original={}),
                     lambda p: p['definitions'][next(iter(p['definitions']))].update(svd_sha256='bad')]
        for mutate in mutations:
            p = copy.deepcopy(payload); mutate(p)
            with self.assertRaises(ValueError): decode(p)

    def test_pending_attempt_survives_failed_result(self):
        j = CompactJournal(**dict(MAXIMUMS_V2, max_records=2))
        with self.assertRaises(Exception): exercise(j)
        rows = decode(j.payload('r', 'c')).records()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1]['name'], 'mmio.attempt')

    def test_config_schema2_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'target.toml').write_text(TARGET)
            (root/'session.toml').write_text('[config]\ntarget="target.toml"\napi="api.toml"\n')
            (root/'api.toml').write_text('schema=2\n[journal]\nrepresentation="compact"\n')
            c = loads(dumps(load_session(root/'session.toml')))
            self.assertEqual(dict(c.config['api']['records']), DEFAULTS_V2)
            self.assertEqual(c.config['api']['journal']['representation'], 'compact')
            from stm32_gdbtest.config_transport import fingerprint
            capsule = json.loads(dumps(load_session(root/'session.toml')))
            capsule['defaults'] = fingerprint()
            with self.assertRaises(ValueError): loads(json.dumps(capsule))
            for key, maximum in MAXIMUMS_V2.items():
                for value, valid in ((1, True), (maximum, True), (0, False),
                                     (maximum + 1, False), ('true', False), ('1.5', False)):
                    (root/'api.toml').write_text(f'schema=2\n[records]\n{key}={value}\n')
                    if valid:
                        self.assertEqual(load_session(root/'session.toml').config['api']['records'][key], value)
                    else:
                        with self.assertRaises(ValueError): load_session(root/'session.toml')
            for value in ('"summary"', 'true', '[]'):
                (root/'api.toml').write_text(f'schema=2\n[journal]\nrepresentation={value}\n')
                with self.assertRaises(ValueError): load_session(root/'session.toml')
            (root/'api.toml').write_text('schema=1\n[journal]\nrepresentation="compact"\n')
            with self.assertRaises(ValueError): load_session(root/'session.toml')

    def test_logical_depth_not_encoding_depth(self):
        for cls in (Journal, CompactJournal):
            j = cls(max_depth=2)
            j.record('depth', [[1]])
            with self.assertRaises(RecordError): j.record('bad', [[[1]]])
            self.assertEqual(j.records()[0]['data'], [[1]])

    def test_materialization_limit_does_not_prevent_streaming(self):
        j = exercise(CompactJournal(**MAXIMUMS_V2))
        with patch('stm32_gdbtest.compact_records.QUERY_NODES', 10):
            with self.assertRaises(RecordError) as cm: j.records()
            self.assertEqual(cm.exception.details['scope'], 'materialization')
            with tempfile.TemporaryDirectory() as folder:
                report = dict(run_id='r', id='c', status='FAIL')
                save(folder, report, SimpleNamespace(_journal=j), 'interrupted')
                finalize(folder, report, True)
                self.assertEqual(report['command_code'], 1)
                self.assertEqual(report['capture']['status'], 'saved')
                self.assertEqual(len(list(read(folder, report, materialize=False)['records'])), 13)
                with self.assertRaises(RecordError): read(folder, report)
        self.assertEqual(len(list(j.iter_records())), 13)

    def test_schema2_real_upper_boundaries(self):
        j = Journal(**MAXIMUMS_V2)
        for _ in range(MAXIMUMS_V2['max_records']): j.record('n', None)
        with self.assertRaises(RecordError) as cm: j.record('n', None)
        self.assertEqual(cm.exception.limit, 'records')
        j = Journal(**MAXIMUMS_V2)
        j.record('n', [None] * (MAXIMUMS_V2['max_nodes'] - 2))
        with self.assertRaises(RecordError) as cm: j.record('n', None)
        self.assertEqual(cm.exception.limit, 'nodes')
        j = Journal(**MAXIMUMS_V2)
        j.record('n', 'x' * (MAXIMUMS_V2['max_text_bytes'] - 1))
        with self.assertRaises(RecordError) as cm: j.record('n', None)
        self.assertEqual(cm.exception.limit, 'text_bytes')

    def test_descriptor_change_and_transport_failure(self):
        from dataclasses import replace
        from stm32_gdbtest.mmio import MMIOError
        j = CompactJournal(**MAXIMUMS_V2)
        reg = Register('P.R', 0x40000000, 32, 'read-write')
        catalog = SimpleNamespace(registers={'P.R': reg}, sha256='a'*64)
        transport = SimpleNamespace(prepare=lambda: None, write=lambda *args: None)
        m = MMIO(catalog, transport, j.mmio_record)
        m.write('P.R', 1)
        catalog.sha256 = 'b'*64
        m.write('P.R', 2)
        m.write('P.R', 3, override=replace(reg, address=0x40000004), reason='model')
        self.assertEqual(len(j.definitions), 3)
        transport.write = lambda *args: (_ for _ in ()).throw(TimeoutError('ACK'))
        with self.assertRaises(MMIOError): m.write('P.R', 4)
        rows = decode(j.payload('r', 'c')).records()
        self.assertEqual(rows[-1]['data']['status'], 'ERROR')
        self.assertEqual(rows[-1]['data']['effect'], 'unknown')

    def test_result_export_reads_compact(self):
        from stm32_gdbtest.result_export import export
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            j = exercise(CompactJournal(**MAXIMUMS_V2))
            report = dict(run_id='r', id='c', status='PASS')
            save(root, report, SimpleNamespace(_journal=j), 'normal')
            path = root/'result.json'; path.write_text(json.dumps(report))
            bundle = export([path], root/'export')
            self.assertEqual(bundle['command_code'], 0)
            self.assertEqual(len(bundle['records']), 13)

    def test_reader_allocates_for_file_not_maximum(self):
        from unittest.mock import MagicMock
        with tempfile.TemporaryDirectory() as d:
            report = dict(run_id='r', id='c', status='PASS')
            save(d, report, SimpleNamespace(_journal=exercise(CompactJournal(**MAXIMUMS_V2))), 'normal')
            raw = Path(d, 'records.json').read_bytes()
            stream = MagicMock()
            stream.__enter__.return_value = stream
            stream.read.return_value = raw
            with patch('pathlib.Path.open', return_value=stream), patch(
                    'stm32_gdbtest.result_capture.os.fstat', return_value=SimpleNamespace(st_size=len(raw))):
                self.assertEqual(len(read(d, report)['records']), 13)
                stream.read.assert_called_once_with(len(raw) + 1)
                stream.read.return_value = raw + b' '
                with self.assertRaises(ValueError): read(d, report)
            with patch('stm32_gdbtest.result_capture.MAX_BYTES', len(raw) - 1):
                with self.assertRaises(ValueError): read(d, report)
