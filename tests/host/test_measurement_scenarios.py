"""Known numerical anchors and invalid publications for all migrated profiles."""
import importlib.util
from pathlib import Path
import unittest

from stm32_gdbtest.matchers import Matcher
from stm32_gdbtest.records import Journal

ROOT = Path(__file__).resolve().parents[2]


class Target(Journal):
    def __init__(self, count=3, bad=None):
        super().__init__()
        # Only the user section of the run profile is read by the measurement scenario.
        self.profile = type('Profile', (), {'user': {'measurement': dict(count=count, expected_quality=2)}})()
        self.index = -1
        self.bad = bad

    def reach(self, name):
        if name == 'board_adc_sample':
            self.index += 1

    # The 0.3.0 names; the scenarios migrated from value().
    def read(self, path, **options):
        return self.value(path)

    def evaluate(self, expression, **options):
        return self.value(expression)

    def value(self, expression):
        if expression == 'board_adc_sequences':
            return 1 if self.bad == 'stale' else self.index + 1
        if expression.endswith('quality'):
            return 0 if self.bad == 'quality' else 2
        if expression.endswith('vdda_mv'):
            return 0 if self.bad == 'range' else 3300 + 2 * self.index
        if expression.endswith('temperature_mdeg_c'):
            return 30000 + 1000 * self.index
        raise AssertionError(expression)

    def check(self, name, actual, expected=True):
        # The same three forms as Target.check: equality, a matcher, or truth without an expectation.
        if isinstance(expected, Matcher):
            passed = expected.matches(actual)
        elif expected is True:
            passed = bool(actual)
        else:
            passed = actual == expected
        if not passed:
            raise AssertionError(name)


class MeasurementScenariosTests(unittest.TestCase):
    def scenarios(self):
        for path in sorted((ROOT/'tests/firmware').glob('common/tests/board/test_measurements.py')):
            spec = importlib.util.spec_from_file_location('measurements', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            yield path, module.adc_series

    def test_known_means_and_sample_deviations(self):
        scenarios = list(self.scenarios())
        self.assertEqual(len(scenarios), 1)
        for path, scenario in scenarios:
            with self.subTest(path=path):
                target = Target()
                scenario(target)
                self.assertEqual(target.records('adc.summary')[0]['data'], dict(count=3, ddof=1,
                    vdda_mv=dict(mean=3302, stdev=2), temperature_c=dict(mean=31, stdev=1)))

    def test_invalid_input_never_produces_summary(self):
        for path, scenario in self.scenarios():
            for bad in ('stale', 'quality', 'range'):
                with self.subTest(path=path, bad=bad):
                    target = Target(bad=bad)
                    with self.assertRaises(AssertionError):
                        scenario(target)
                    self.assertEqual(target.records('adc.summary'), [])
            for count in (True, 1, 21):
                with self.subTest(path=path, count=count):
                    target = Target(count=count)
                    with self.assertRaises(AssertionError):
                        scenario(target)
                    self.assertEqual(target.index, -1)
