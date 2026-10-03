"""Independent numerical anchors and scripted target checks, not HW evidence."""

import unittest

from evidence import Journal
from measurement_series import f411_measurement_series, summarize


class ScriptedTarget:
    def __init__(self, sequences=(1, 2, 3), quality=2):
        self.sequences = sequences
        self.quality = quality
        self.index = -1
        self.stops = []

    def reach(self, name):
        self.stops.append(name)
        if name == "board_delay_ms":
            self.index += 1

    def value(self, expression):
        return {"board_adc_sequences": self.sequences[self.index],
                "board_adc_reading.quality": self.quality,
                "board_adc_reading.vdda_mv": (3200, 3300, 3400)[self.index],
                "board_adc_reading.temperature_mdeg_c": (24000, 25000, 26000)[self.index]}[expression]

    def check(self, name, actual, expected):
        if actual != expected:
            raise AssertionError(name)


class MeasurementTests(unittest.TestCase):
    def test_known_mean_and_sample_deviation(self):
        target = ScriptedTarget()
        result, entries = f411_measurement_series(target, 3)
        self.assertEqual(result, {
            "count": 3, "vdda": {"unit": "mV", "mean": 3300, "stdev": 100},
            "temperature": {"unit": "degC", "mean": 25, "stdev": 1}, "stdev_ddof": 1})
        self.assertEqual(target.stops, ["board_adc_sample", "board_delay_ms"] * 3)
        self.assertEqual(len(entries), 4)
        self.assertEqual(entries[0]["data"]["temperature_mdeg_c"], 24000)

    def test_duplicate_and_missing_acquisitions(self):
        for sequences in ((1, 1, 2), (1, 3, 4)):
            with self.assertRaisesRegex(AssertionError, "new ADC sequence"):
                f411_measurement_series(ScriptedTarget(sequences), 3)

    def test_sequence_wrap(self):
        result, _ = f411_measurement_series(ScriptedTarget((0xFFFFFFFF, 0, 1)), 3)
        self.assertEqual(result["count"], 3)

    def test_invalid_quality(self):
        with self.assertRaisesRegex(AssertionError, "measurement provenance"):
            f411_measurement_series(ScriptedTarget(quality=0), 3)

    def test_short_series_and_bad_counts(self):
        t = Journal()
        with self.assertRaisesRegex(ValueError, "at least two"):
            summarize(t)
        t.record("mcu.measurement", {"sequence": 1})
        with self.assertRaisesRegex(ValueError, "at least two"):
            summarize(t)
        for count in (0, 1, 101, True, 2.5):
            with self.assertRaises(ValueError):
                f411_measurement_series(ScriptedTarget(), count)

    def test_summary_rejects_duplicates_and_bad_quality(self):
        for second in ({"sequence": 1, "quality": 2}, {"sequence": 2, "quality": 0}):
            t = Journal()
            t.record("mcu.measurement", {"sequence": 1, "quality": 2})
            t.record("mcu.measurement", second)
            with self.assertRaises(ValueError):
                summarize(t)
            self.assertEqual(t.records("mcu.summary"), [])
