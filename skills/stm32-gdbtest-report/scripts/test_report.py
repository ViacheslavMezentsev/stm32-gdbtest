"""Проверка связей входов генератора; нужны зависимости самого навыка."""
import copy
import json
from pathlib import Path
import unittest

from render_report import validate


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((Path(__file__).resolve().parents[1] /
                                'references/example.json').read_text(encoding='utf-8'))

    def test_valid_inputs(self):
        validate(self.data)
        validate(json.loads((Path(__file__).resolve().parents[1] /
                             'references/acceptance-050.json').read_text(encoding='utf-8')))

    def test_unknown_method(self):
        self.data['evidence'][0]['method_ids'] = ['missing']
        with self.assertRaisesRegex(ValueError, 'evidence method'):
            validate(self.data)

    def test_duplicate_ids(self):
        for kind in ('methods', 'evidence'):
            data = copy.deepcopy(self.data)
            data[kind].append(copy.deepcopy(data[kind][0]))
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                validate(data)

    def test_required_observations(self):
        self.data['evidence'][0]['rows'] = []
        with self.assertRaisesRegex(ValueError, 'table'):
            validate(self.data)

    def test_unknown_chart_value(self):
        self.data['evidence'][1]['chart']['observed'][0] = None
        with self.assertRaisesRegex(ValueError, 'unknown/nonfinite'):
            validate(self.data)

    def test_chart_labels(self):
        self.data['evidence'][1]['chart']['labels'] = ['one']
        with self.assertRaisesRegex(ValueError, 'labels'):
            validate(self.data)


if __name__ == '__main__':
    unittest.main()
