"""Actual Target delegation and immutable views, with only GDB events substituted."""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest import RecordError
from stm32_gdbtest.configuration import Configuration, DEFAULTS, freeze


class TargetRecordsTests(unittest.TestCase):
    def setUp(self):
        fake = types.SimpleNamespace(events=types.SimpleNamespace(stop=Mock()))
        previous = sys.modules.pop('stm32_gdbtest.target', None)
        with patch.dict(sys.modules, gdb=fake):
            self.module = importlib.import_module('stm32_gdbtest.target')
        sys.modules.pop('stm32_gdbtest.target', None)
        if previous is not None:
            sys.modules['stm32_gdbtest.target'] = previous
        self.config = Configuration(freeze(dict(target={}, image=None,
            api=dict(schema=1, records={**DEFAULTS, 'max_records': 2, 'custom': 999}))),
            freeze(dict(target=None, api=None, image=None)), None, {})

    def test_records_are_local_detached_and_not_report_checks(self):
        report = {'checks': []}
        first = self.module.Target(report, {}, self.config)
        second = self.module.Target({'checks': []}, {}, self.config)
        source = [1]
        self.assertIsNone(first.record('a', source))
        source[0] = 2
        self.assertEqual(first.records()[0]['data'], [1])
        self.assertEqual(second.records(), [])
        self.assertEqual(report, {'checks': []})
        first.clear()
        self.assertEqual(first.records()[0]['data'], [1])
        with self.assertRaises(self.module.CheckFailed):
            first.check('failed', 0, 1)
        self.assertEqual(first.records()[0]['data'], [1])
        first.record('b', 2)
        with self.assertRaises(RecordError) as caught:
            first.record('c', 3)
        self.assertEqual(caught.exception.limit, 'records')
        self.assertEqual(len(first.records()), 2)

    def test_config_properties_are_read_only(self):
        target = self.module.Target({'checks': []}, {}, self.config)
        for name in ('config', 'config_props'):
            with self.assertRaises(AttributeError):
                setattr(target, name, {})
        with self.assertRaises(TypeError):
            target.config['api']['records']['max_records'] = 4
        self.assertEqual(target.config['api']['records']['custom'], 999)
