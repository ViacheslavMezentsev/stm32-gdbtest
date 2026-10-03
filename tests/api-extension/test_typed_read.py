"""E2 controlled backend checks; actual GDB behavior requires hardware evidence."""

from dataclasses import FrozenInstanceError
import unittest

from typed_read import Reader, ReadError


def scalar(value, **overrides):
    return dict(kind='int', type='int32_t', size=4, address=0x20000000,
                unavailable=None, bounds=None, data=value, **overrides)


class Backend:
    errors = (OSError, KeyError)

    def __init__(self):
        self.reads = 0
        self.lookups = 0
        self.stopped = True
        self.values = {'counter': scalar(-7),
                       'samples': dict(kind='array', type='uint16_t [2]', size=4,
                                       address=0x20000010, unavailable=None, bounds=(0, 1),
                                       data=[scalar(100), scalar(200)]),
                       'reading': dict(kind='struct', type='reading_t', size=12,
                                       address=0x20000020, unavailable=None, bounds=None,
                                       data={'vdda': scalar(3300), 'temperature': scalar(-1250)})}

    def ensure_stopped(self):
        if not self.stopped:
            raise ReadError('not_stopped', '')

    def global_value(self, name):
        self.lookups += 1
        if name not in self.values:
            raise ReadError('missing_symbol', name)
        return self.values[name]

    def describe(self, value):
        return value

    def child(self, value, key):
        return value['data'][key]

    def scalar(self, value, kind):
        self.reads += 1
        if value['data'] == 'error':
            raise OSError('memory failure')
        return value['data']


class ReadTests(unittest.TestCase):
    def setUp(self):
        self.backend = Backend()
        self.reader = Reader(self.backend, ram_ranges=((0x20000000, 0x20020000),))

    def test_scalar_array_fields_and_immutable_snapshot(self):
        self.assertEqual(self.reader.read('counter').value, -7)
        result = self.reader.read('samples', count=2)
        self.assertEqual([v.value for _, v in result.value], [100, 200])
        self.assertEqual(result.type_name, 'uint16_t [2]')
        selected = self.reader.read('reading', fields=('temperature', 'vdda'))
        self.assertEqual([(k, v.value) for k, v in selected.value], [('temperature', -1250), ('vdda', 3300)])
        self.backend.values['reading']['data']['vdda']['data'] = 999
        self.assertEqual(selected.value[1][1].value, 3300)
        with self.assertRaises(FrozenInstanceError):
            result.value = ()

    def test_paths(self):
        self.assertEqual(self.reader.read('samples[1]').value, 200)
        self.assertEqual(self.reader.read('reading.vdda').value, 3300)

    def test_expressions_rejected_before_lookup(self):
        for path in ('fn()', 'counter=1', '++counter', '*ptr', 'ptr->field', '$pc', 'samples[-1]'):
            with self.assertRaises(ReadError) as caught:
                self.reader.read(path)
            self.assertEqual(caught.exception.code, 'invalid_path')
        self.assertEqual(self.backend.lookups, 0)

    def test_selection_and_bounds(self):
        for path, options in [('samples', {}), ('reading', {}), ('samples', {'count':3}),
                              ('reading', {'fields':('vdda','vdda')}),
                              ('counter', {'count':1}), ('samples[2]', {})]:
            with self.subTest(path=path, options=options), self.assertRaises(ReadError):
                self.reader.read(path, **options)

    def test_unavailable_and_no_implicit_pointer_or_mmio(self):
        for change, code in [({'address':0x40000000}, 'outside_ram'),
                             ({'kind':'unsupported'}, 'unsupported_type'),
                             ({'unavailable':'optimized_out'}, 'optimized_out')]:
            self.backend.values['counter'] = scalar(1)
            self.backend.values['counter'].update(change)
            with self.assertRaises(ReadError) as caught:
                self.reader.read('counter')
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.backend.reads, 0)

    def test_missing_memory_and_running(self):
        with self.assertRaises(ReadError) as caught:
            self.reader.read('absent')
        self.assertEqual(caught.exception.code, 'missing_symbol')
        self.backend.values['counter']['data'] = 'error'
        with self.assertRaises(ReadError) as caught:
            self.reader.read('counter')
        self.assertEqual(caught.exception.code, 'unreadable')
        self.backend.stopped = False
        with self.assertRaises(ReadError) as caught:
            self.reader.read('counter')
        self.assertEqual(caught.exception.code, 'not_stopped')

    def test_resource_limits(self):
        for limits in ({'max_bytes':3}, {'max_nodes':1}):
            reader = Reader(self.backend, ram_ranges=self.reader.ranges, **limits)
            with self.assertRaises(ReadError):
                reader.read('samples', count=2)
        for options in ({'max_nodes':True}, {'max_bytes':0}):
            with self.assertRaises(ValueError):
                Reader(self.backend, ram_ranges=self.reader.ranges, **options)
