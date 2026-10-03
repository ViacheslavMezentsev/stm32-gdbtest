"""Host-only E1 contracts and Python query examples; no MCU simulation claim."""

import unittest

from evidence import Journal, RecordError, RecordingTarget


class RecordTests(unittest.TestCase):
    def test_order_and_duplicate_names(self):
        t = Journal()
        self.assertIsNone(t.record("adc", 100))
        t.record("irq", None)
        t.record("adc", 200)
        self.assertEqual(t.records(), [
            {"sequence": 1, "name": "adc", "data": 100},
            {"sequence": 2, "name": "irq", "data": None},
            {"sequence": 3, "name": "adc", "data": 200},
        ])
        self.assertEqual([r["sequence"] for r in t.records("adc")], [1, 3])

    def test_write_and_read_snapshots(self):
        t = Journal()
        source = {"samples": [100, {"raw": 200}]}
        t.record("adc", source)
        source["samples"][1]["raw"] = 999
        result = t.records()
        result[0]["data"]["samples"].append(300)
        result[0]["data"]["samples"][1]["raw"] = 888
        result.clear()
        self.assertEqual(t.records()[0]["data"], {"samples": [100, {"raw": 200}]})

    def test_supported_scalars_and_shared_children(self):
        t = Journal()
        shared = [None, True, False, -5, 2.5, "измерение"]
        t.record("types", [shared, shared])
        result = t.records()[0]["data"]
        self.assertEqual(result, [shared, shared])
        result[0].append(42)
        self.assertEqual(result[1], shared)

    def test_where_select_take_skip_first_last(self):
        t = Journal()
        for raw in (100, 2100, 2200, 300, 2300):
            t.record("adc", {"raw": raw})
        entries = t.records("adc")
        selected = [r for r in entries if r["data"]["raw"] > 2000]
        self.assertEqual([r["data"]["raw"] for r in selected], [2100, 2200, 2300])
        self.assertEqual([r["sequence"] for r in entries[:3]], [1, 2, 3])
        self.assertEqual([r["sequence"] for r in entries[-2:]], [4, 5])
        self.assertEqual([r["sequence"] for r in entries[3:]], [4, 5])
        self.assertEqual([r["sequence"] for r in entries[1:3]], [2, 3])
        self.assertEqual(next((r for r in entries if r["data"]["raw"] > 2000), None), entries[1])
        self.assertEqual(entries[-1]["data"]["raw"], 2300)
        self.assertTrue(any(r["data"]["raw"] < 200 for r in entries))
        self.assertFalse(all(r["data"]["raw"] > 2000 for r in entries))

    def test_empty_queries_and_short_slices(self):
        entries = Journal().records("missing")
        self.assertEqual(entries[:3], [])
        self.assertEqual(entries[-2:], [])
        self.assertIsNone(next(iter(entries), None))
        self.assertIsNone(entries[-1] if entries else None)
        self.assertFalse(any(entries))
        self.assertTrue(all(entries))
        self.assertFalse(bool(entries) and all(r["data"] > 0 for r in entries))
        t = Journal()
        t.record("one", 1)
        self.assertEqual(len(t.records()[:3]), 1)
        self.assertEqual(t.records()[3:], [])

    def test_filter_then_take_differs_from_take_then_filter(self):
        t = Journal()
        for raw in (0, 10, 20, 30):
            t.record("adc", raw)
        entries = t.records()
        self.assertEqual([r["data"] for r in entries if r["data"] > 0][:2], [10, 20])
        self.assertEqual([r["data"] for r in entries[:2] if r["data"] > 0], [10])

    def test_rejected_values_leave_no_partial_record(self):
        cyclic = []
        cyclic.append(cyclic)
        bad_values = [object(), (1, 2), {1: "bad"}, float("nan"),
                      float("inf"), b"bytes", cyclic, "\ud800", 1 << 256]
        for bad in bad_values:
            with self.subTest(kind=type(bad).__name__):
                t = Journal()
                t.record("before", 1)
                with self.assertRaises(RecordError):
                    t.record("bad", ["valid prefix", bad])
                t.record("after", 2)
                self.assertEqual([r["sequence"] for r in t.records()], [1, 2])
                self.assertEqual([r["name"] for r in t.records()], ["before", "after"])

    def test_rejects_subclasses_without_calling_user_code(self):
        class Dangerous(list):
            def __iter__(self):
                raise AssertionError("must not iterate arbitrary objects")
        with self.assertRaises(RecordError):
            Journal().record("bad", Dangerous())

    def test_names_and_filters(self):
        for value in ("", 3, [], False):
            with self.subTest(value=value):
                with self.assertRaises(RecordError):
                    Journal().record(value, 1)
                with self.assertRaises(RecordError):
                    Journal().records(value)

    def test_limits_and_failure_does_not_consume_budget(self):
        t = Journal(max_records=2, max_nodes=4, max_text_bytes=4)
        with self.assertRaises(RecordError):
            t.record("a", "oversize")
        t.record("a", 1)
        t.record("b", 2)
        with self.assertRaises(RecordError):
            t.record("c", 3)
        self.assertEqual(len(t.records()), 2)
        for kwargs, data in (({"max_nodes": 2}, [1]),
                             ({"max_depth": 1}, [[1]]),
                             ({"max_text_bytes": 2}, "я")):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(RecordError):
                    Journal(**kwargs).record("a", data)

    def test_invalid_limit_configuration(self):
        for limit in (0, -1, True, 1.5):
            with self.assertRaises(ValueError):
                Journal(max_records=limit)

    def test_journals_are_per_invocation(self):
        target = object()
        first, second = RecordingTarget(target), RecordingTarget(target)
        first.record("sample", 1)
        self.assertEqual(second.records(), [])

    def test_target_failure_propagates_and_evidence_remains(self):
        class FailedCheck(Exception):
            pass
        failure = FailedCheck("original failure")
        class Target:
            def check(self):
                raise failure
        t = RecordingTarget(Target())
        t.record("before", 42)
        with self.assertRaises(FailedCheck) as caught:
            t.check()
        self.assertIs(caught.exception, failure)
        self.assertEqual(t.records()[0]["data"], 42)


if __name__ == "__main__":
    unittest.main()
