"""Compare explicit tables to independently executed original board functions."""
import importlib.util
from pathlib import Path
import unittest

import table_variants as variants
from table_checks import check_values

ROOT = Path(__file__).resolve().parents[2]
CASES = [
    ('tests/firmware/profiles/f030r8/tests/board/test_rtc.py', 'rtc_init', variants.f030_rtc, variants.F030_RTC),
    ('tests/firmware/profiles/f411ce/tests/board/test_adc.py', 'adc_init', variants.f411_adc, variants.F411_ADC),
    ('tests/firmware/profiles/f103c8/tests/board/test_ci.py', 'timer_init', variants.f103_timer, variants.F103_TIMER),
]


class Observations:
    def __init__(self, values, bad_check=None, bad_read=None):
        self.values = values
        self.bad_check, self.bad_read = bad_check, bad_read
        self.trace = []
        self.checks = self.reads = 0

    def reach(self, expression):
        self.trace.append(('reach', expression))

    def value(self, expression):
        self.trace.append(('value', expression))
        self.reads += 1
        if self.reads == self.bad_read:
            raise RuntimeError('unreadable: ' + expression)
        return self.values[expression]

    def check(self, name, actual, expected):
        self.trace.append(('check', name, actual, expected))
        self.checks += 1
        if actual != expected or self.checks == self.bad_check:
            raise AssertionError(name)


class TableChecksTests(unittest.TestCase):
    def compare(self, bad_kind=None):
        for path, name, variant, rows in CASES:
            spec = importlib.util.spec_from_file_location('table_original', ROOT/path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            original = getattr(module, name)
            values = {}
            for index, (_, expression, expected) in enumerate(rows):
                if isinstance(expected, str):
                    values[expected] = 0x1000 + index
                    expected = values[expected]
                values[expression] = expected
            count = (len(rows) if bad_kind == 'check' else
                     len(rows) + sum(isinstance(r[2], str) for r in rows))
            points = range(1, count + 1) if bad_kind else [None]
            for point in points:
                with self.subTest(scenario=name, kind=bad_kind, point=point):
                    targets = [Observations(values, point if bad_kind == 'check' else None,
                                            point if bad_kind == 'read' else None) for _ in range(2)]
                    outcomes = []
                    for function, target in zip((original, variant), targets):
                        try:
                            function(target)
                            outcomes.append(None)
                        except (AssertionError, RuntimeError) as exc:
                            outcomes.append((type(exc), str(exc)))
                    self.assertEqual(outcomes[0], outcomes[1])
                    self.assertEqual(targets[0].trace, targets[1].trace)
                    if bad_kind:
                        self.assertIsNotNone(outcomes[0])
                    else:
                        self.assertIsNone(outcomes[0])
                        self.assertEqual(targets[0].checks, len(rows))

    def test_success_preserves_all_observations(self):
        self.compare()

    def test_each_check_failure_stops_at_same_label(self):
        self.compare('check')

    def test_each_read_failure_preserves_order_and_stop(self):
        self.compare('read')

    def test_empty_table_has_no_effect(self):
        target = Observations({})
        check_values(target, [])
        self.assertEqual(target.trace, [])

    def test_expected_expression_is_not_evaluated_ahead(self):
        target = Observations({'first': 1, 'actual': 2, 'expected': 2}, bad_check=1)
        with self.assertRaises(AssertionError):
            check_values(target, [('first check', 'first', 1), ('later', 'actual', 'expected')])
        self.assertEqual(target.trace, [('value', 'first'), ('check', 'first check', 1, 1)])
