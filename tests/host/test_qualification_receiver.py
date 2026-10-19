"""Independent journal validation for the emulator qualification example (ТЗ 5.28)."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

BASE = Path(__file__).resolve().parents[2] / 'examples/ddtt-qualification'
spec = importlib.util.spec_from_file_location('qualification_renode', BASE/'run_renode.py')
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name)/'receiver.jsonl'

    def model(self, drop=0):
        scope = dict(DROP_SEQUENCE=drop, TRACE_PATH=str(self.path),
                     request=SimpleNamespace(IsInit=True, IsWrite=False, IsRead=False))
        code = compile((BASE/'receiver.py').read_text(encoding='utf-8'), 'receiver.py', 'exec')
        exec(code, scope)
        for value in (1, 2, 3):
            scope['request'] = SimpleNamespace(IsInit=False, IsWrite=True, IsRead=False,
                                              Offset=0, Length=4, Value=value)
            exec(code, scope)
        return [json.loads(line) for line in self.path.read_text().splitlines()]

    def test_nominal_and_drop(self):
        for drop, count in ((0, 3), (2, 2)):
            with self.subTest(drop=drop):
                self.path.unlink(missing_ok=True)
                self.model(drop)
                self.assertEqual(example.receipt(self.path), count)

    def test_missing_journal_is_not_zero(self):
        with self.assertRaises(FileNotFoundError):
            example.receipt(self.path)

    def test_incomplete_and_duplicate(self):
        rows = self.model()
        for events in ([], rows[:2], rows + rows[:1], [rows[0], rows[0], rows[2]]):
            with self.subTest(events=events):
                self.path.write_text('\n'.join(json.dumps(e) for e in events))
                with self.assertRaises(ValueError):
                    example.receipt(self.path)

    def test_wrong_width_value_or_acceptance(self):
        for field, value in (('width', 1), ('value', 7), ('accepted', 1), ('offset', 4)):
            with self.subTest(field=field):
                self.path.unlink(missing_ok=True)
                rows = self.model()
                rows[1][field] = value
                self.path.write_text('\n'.join(json.dumps(e) for e in rows))
                with self.assertRaises(ValueError):
                    example.receipt(self.path)

    def test_truncated_json(self):
        self.path.write_text('{')
        with self.assertRaises(ValueError):
            example.receipt(self.path)


if __name__ == '__main__':
    unittest.main()
