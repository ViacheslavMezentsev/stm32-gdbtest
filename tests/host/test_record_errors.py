"""API specification 5.3/5.4: integrated record error contracts."""
import unittest
from unittest.mock import patch

from stm32_gdbtest.records import Journal, RecordError


class RecordErrorTests(unittest.TestCase):
    def test_data_codes_preserve_history_and_sequence(self):
        cyclic = []
        cyclic.append(cyclic)
        class Subclass(int):
            pass
        cases = [('unsupported_type', object()), ('unsupported_type', b'x'),
                 ('unsupported_type', (1,)), ('unsupported_type', {1: 2}),
                 ('unsupported_type', Subclass(1)), ('invalid_text', '\ud800'),
                 ('invalid_text', {'\udfff': 1}), ('non_finite', float('nan')),
                 ('non_finite', float('inf')), ('non_finite', -float('inf')),
                 ('cycle', cyclic)]
        for code, value in cases:
            with self.subTest(code=code, kind=type(value).__name__):
                journal = Journal()
                journal.record('before', [1])
                with self.assertRaises(RecordError) as caught:
                    journal.record('bad', ['valid prefix', value])
                self.assertEqual(caught.exception.code, code)
                self.assertIsNone(caught.exception.limit)
                journal.record('after', [2])
                self.assertEqual(journal.records(), [
                    {'sequence': 1, 'name': 'before', 'data': [1]},
                    {'sequence': 2, 'name': 'after', 'data': [2]}])

    def test_names_and_filters_have_machine_code(self):
        class Subclass(str):
            pass
        for value in ('', 0, False, [], Subclass('s')):
            for method in ('record', 'records'):
                with self.subTest(method=method, value=value):
                    journal = Journal()
                    with self.assertRaises(RecordError) as caught:
                        if method == 'record':
                            journal.record(value, 1)
                        else:
                            journal.records(value)
                    self.assertEqual(caught.exception.code, 'invalid_name')
                    self.assertEqual(journal.records(), [])
        with self.assertRaises(RecordError) as caught:
            Journal().record('\ud800', 1)
        self.assertEqual(caught.exception.code, 'invalid_text')

    def test_each_limit_and_atomic_budget(self):
        cases = [('nodes', {'max_nodes': 4}, [1, 2, 3]),
                 ('depth', {'max_depth': 1}, [[1]]),
                 ('text_bytes', {'max_text_bytes': 2}, 'xx'),
                 ('text_bytes', {'max_text_bytes': 2}, '\u044f'),
                 ('integer_bits', {'max_integer_bits': 2}, 4)]
        for limit, settings, value in cases:
            with self.subTest(limit=limit, value=value):
                journal = Journal(**settings)
                with self.assertRaises(RecordError) as caught:
                    journal.record('s', value)
                self.assertEqual((caught.exception.code, caught.exception.limit),
                                 ('limit_exceeded', limit))
                # Two small writes fill exactly the tightest node/text budgets.
                journal.record('a', 1)
                journal.record('b', 2)
                self.assertEqual([r['sequence'] for r in journal.records()], [1, 2])
        journal = Journal(max_records=1)
        journal.record('a', 1)
        with self.assertRaises(RecordError) as caught:
            journal.record('b', 2)
        self.assertEqual((caught.exception.code, caught.exception.limit),
                         ('limit_exceeded', 'records'))
        self.assertEqual(journal.records(), [{'sequence': 1, 'name': 'a', 'data': 1}])

    def test_system_error_is_not_disguised(self):
        journal = Journal()
        journal.record('before', 1)
        failure = MemoryError('injected allocation failure')
        with patch.object(journal, '_copy', side_effect=failure):
            with self.assertRaises(MemoryError) as caught:
                journal.record('s', 2)
        self.assertIs(caught.exception, failure)
        journal.record('after', 2)
        self.assertEqual([r['sequence'] for r in journal.records()], [1, 2])

    def test_caught_error_allows_explicit_recovery(self):
        journal = Journal(max_integer_bits=8)
        try:
            journal.record('overflow', 256)
        except RecordError as error:
            self.assertEqual(error.code, 'limit_exceeded')
            self.assertEqual(error.limit, 'integer_bits')
            journal.record('diagnostic', {'rejected': True})
        self.assertEqual(journal.records()[0]['sequence'], 1)
        self.assertEqual(journal.records()[0]['name'], 'diagnostic')
