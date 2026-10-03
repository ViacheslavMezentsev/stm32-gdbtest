"""Compare original source functions with variants on controlled observations."""

import importlib.util
from pathlib import Path
import sys
import unittest

from evidence import RecordingTarget
import scenario_variants as variants

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def load(relative):
    spec = importlib.util.spec_from_file_location("original", ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CMSIS = load("tests/firmware/profiles/f411ce/tests/board/test_adc.py")
HAL = load("tests/hal-f030/hal_scenarios/peripheral_runtime.py")
BOARD = load("tests/hal-f030/hal_scenarios/board.py")


class Observations:
    def __init__(self, values, fail_read=None):
        self.values = {k: iter(v) for k, v in values.items()}
        self.fail_read = fail_read
        self.calls = []
        self.report = {}

    def reach(self, location):
        self.calls.append(("reach", location))

    def value(self, expression):
        self.calls.append(("value", expression))
        if expression == self.fail_read:
            raise RuntimeError("unavailable: " + expression)
        return next(self.values[expression])

    def check(self, name, actual, expected):
        self.calls.append(("check", name, actual, expected))
        if actual != expected:
            raise AssertionError(name)


class PairTests(unittest.TestCase):
    def compare(self, original, variant, values, args=(), fail_read=None):
        left, right = Observations(values, fail_read), Observations(values, fail_read)
        wrapped = RecordingTarget(right)
        outcomes = []
        for fn, target in ((original, left), (variant, wrapped)):
            try:
                fn(target, *args)
                outcomes.append(None)
            except (AssertionError, RuntimeError) as exc:
                outcomes.append((type(exc), str(exc)))
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(left.calls, right.calls)
        self.assertEqual(right.report, {})
        if "measurement" in left.report:
            self.assertEqual(wrapped.records("measurement")[0]["data"], left.report["measurement"])
        else:
            self.assertEqual(wrapped.records("measurement"), [])
        if "loop_tick_deltas_ms" in left.report:
            self.assertEqual([r["data"] for r in wrapped.records("loop_tick_deltas_ms")],
                             left.report["loop_tick_deltas_ms"])
        return outcomes[0]

    def test_adc_positive_boundaries_and_negative_checks(self):
        for prefix, original, variant, args in (
            ("board_adc_reading.", CMSIS.adc_units, variants.cmsis_adc_units, ()),
            ("app_state.measurement.", HAL.adc_units, variants.hal_adc_units, ({"measurement_quality": 2},)),
        ):
            for quality, vdda, temp in ((2, 3300, 25000), (2, 2800, -40000),
                                        (2, 3600, 125000), (0, 3300, 25000),
                                        (2, 2799, 25000), (2, 3601, 25000),
                                        (2, 3300, -40001), (2, 3300, 125001)):
                with self.subTest(prefix=prefix, values=(quality, vdda, temp)):
                    values = {prefix + k: [v, v] for k, v in
                              (("quality", quality), ("vdda_mv", vdda), ("temperature_mdeg_c", temp))}
                    outcome = self.compare(original, variant, values, args)
                    self.assertEqual(outcome is None, quality == 2 and 2800 <= vdda <= 3600
                                     and -40000 <= temp <= 125000)

    def test_unavailable_read(self):
        for original, variant, prefix, args in (
            (CMSIS.adc_units, variants.cmsis_adc_units, "board_adc_reading.", ()),
            (HAL.adc_units, variants.hal_adc_units, "app_state.measurement.", ({"measurement_quality": 2},)),
        ):
            values = {prefix + "quality": [2], prefix + "vdda_mv": [3300]}
            result = self.compare(original, variant, values, args, prefix + "temperature_mdeg_c")
            self.assertIs(result[0], RuntimeError)

    def test_blink_repetition_wrap_and_failures(self):
        for ticks, levels, passes in (((0, 500, 1000), (1, 0), True),
                                     ((0xFFFFFF00, 244, 744), (1, 0), True),
                                     ((0, 499, 1000), (1, 0), False),
                                     ((0, 500, 1000), (0, 0), False)):
            with self.subTest(ticks=ticks, levels=levels):
                result = self.compare(BOARD.blink, variants.hal_blink,
                                      {"uwTick": ticks, "led": levels},
                                      ({"led_initial": 0, "led_level": "led"},))
                self.assertEqual(result is None, passes)
