"""TECH-011 paired sequence and independent arithmetic tests, no MCU."""
from types import SimpleNamespace
import unittest

from evidence import RecordingTarget
from measurement_series import f411_measurement_series
from measurement_technique import configured_series, mean_in_gdb
from session_config import freeze, DEFAULTS
from session_pipeline import ConfiguredTarget
from test_measurement_series import ScriptedTarget


class TraceTarget(ScriptedTarget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trace = []

    def reach(self, name):
        self.trace.append(('reach', name))
        super().reach(name)

    def value(self, expression):
        self.trace.append(('value', expression))
        return super().value(expression)

    def check(self, name, actual, expected):
        self.trace.append(('check', name, actual, expected))
        super().check(name, actual, expected)


class FakeGdb:
    Value = int

    def __init__(self, fail=False):
        self.state = {'ddtt_tech011_sum': 17}
        self.fail = fail

    def convenience_variable(self, name):
        return self.state.get(name)

    def set_convenience_variable(self, name, value):
        if value is None:
            self.state.pop(name, None)
        else:
            self.state[name] = value

    def parse_and_eval(self, expression):
        if self.fail:
            raise RuntimeError('injected expression failure')
        return self.state['ddtt_tech011_sum'] / self.state['ddtt_tech011_count']


class MeasurementTechniqueTests(unittest.TestCase):
    def test_configured_variant_matches_old_series(self):
        for sequences, quality in [((1, 2, 3), 2), ((0xFFFFFFFF, 0, 1), 2),
                                   ((1, 1, 2), 2), ((1, 3, 4), 2), ((1, 2, 3), 0)]:
            with self.subTest(sequences=sequences, quality=quality):
                original, variant = TraceTarget(sequences, quality), TraceTarget(sequences, quality)
                snapshot = SimpleNamespace(config=freeze({'api': {'records': dict(DEFAULTS),
                    'user': {'measurement': {'count': 3, 'expected_quality': 2}}}}))
                t = RecordingTarget(ConfiguredTarget(variant, snapshot), **snapshot.config['api']['records'])
                outcomes = []
                for call in (lambda: f411_measurement_series(original, 3), lambda: configured_series(t)):
                    try:
                        outcomes.append(call())
                    except AssertionError as exc:
                        outcomes.append(str(exc))
                self.assertEqual(outcomes[0], outcomes[1])
                self.assertEqual(original.trace, variant.trace)
                if quality != 2 or sequences in ((1, 1, 2), (1, 3, 4)):
                    self.assertEqual(t.records('mcu.summary'), [])

    def test_gdb_mean_and_restoration(self):
        for values, expected in [([3200, 3300, 3400], 3300), ([-1000, 0, 1000], 0),
                                 ([24000, 25000, 26000], 25000), ([1, 2], 1.5)]:
            gdb = FakeGdb()
            self.assertEqual(mean_in_gdb(values, gdb), expected)
            self.assertEqual(gdb.state, {'ddtt_tech011_sum': 17})

    def test_failure_restores_gdb_scratch(self):
        gdb = FakeGdb(fail=True)
        with self.assertRaises(RuntimeError):
            mean_in_gdb([1, 2], gdb)
        self.assertEqual(gdb.state, {'ddtt_tech011_sum': 17})

    def test_invalid_aggregate_has_no_gdb_effect(self):
        for values in ([], [True], [1.5], [1 << 63], [-(1 << 63), -1]):
            gdb = FakeGdb()
            with self.assertRaises(ValueError):
                mean_in_gdb(values, gdb)
            self.assertEqual(gdb.state, {'ddtt_tech011_sum': 17})


def verify_real_gdb(gdb):
    """Called explicitly by the offline GDB experiment, not host discovery."""
    before = [gdb.convenience_variable(n) for n in ('ddtt_tech011_sum', 'ddtt_tech011_count')]
    results = []
    for values, expected in [([3200, 3300, 3400], 3300.0),
                             ([24000, 25000, 26000], 25000.0),
                             ([-1000, 0, 1000], 0.0), ([1, 2], 1.5)]:
        result = mean_in_gdb(values, gdb)
        assert result == expected
        results.append({'values': values, 'mean': result})
    after = [gdb.convenience_variable(n) for n in ('ddtt_tech011_sum', 'ddtt_tech011_count')]
    assert before == after
    return results
