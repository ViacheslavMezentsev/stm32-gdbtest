"""Operation failures, check mismatches and their diagnostic vocabulary (ТЗ API 0.3.0)."""
import unittest

from stm32_gdbtest import ApiError, CheckFailed, RecordError
from stm32_gdbtest.errors import EFFECTS, OPERATIONS, STAGES, fail


class ApiErrorTests(unittest.TestCase):
    def test_public_imports_without_gdb(self):
        import sys
        self.assertNotIn("gdb", sys.modules)
        self.assertTrue(issubclass(ApiError, Exception))
        self.assertTrue(issubclass(CheckFailed, ApiError))
        self.assertTrue(issubclass(CheckFailed, AssertionError))
        self.assertTrue(issubclass(RecordError, ApiError))
        self.assertTrue(issubclass(RecordError, ValueError))

    def test_check_failed_carries_its_check(self):
        error = CheckFailed("ticks advanced", actual=1, expected=2)
        self.assertEqual(error.name, "ticks advanced")
        self.assertEqual(error.code, "mismatch")
        self.assertEqual(error.details["actual"], 1)
        self.assertEqual(error.details["expected"], 2)
        self.assertEqual(str(error), "check failed: ticks advanced")

    def test_record_error_keeps_the_public_attributes(self):
        error = RecordError("limit_exceeded", "record limit exceeded", limit="records")
        self.assertEqual(error.code, "limit_exceeded")
        self.assertEqual(error.limit, "records")
        self.assertEqual(error.details["limit"], "records")
        self.assertEqual(str(error), "record limit exceeded")

        # Without a limit the attribute stays None, as before 0.3.0.
        plain = RecordError("invalid_name", "name must be a non-empty string")
        self.assertIsNone(plain.limit)
        self.assertIsNone(plain.details["limit"])

    def test_fail_validates_the_vocabulary(self):
        with self.assertRaises(ApiError) as caught:
            fail("read", "observe", "none", "conversion_failed", "conversion failed")
        details = caught.exception.details
        self.assertEqual((details["operation"], details["stage"], details["effect"]),
                         ("read", "observe", "none"))
        self.assertEqual(details["code"], "conversion_failed")

    def test_fail_rejects_unknown_vocabulary(self):
        with self.assertRaises(ValueError):
            fail("no_such_operation", "observe", "none", "code", "message")
        with self.assertRaises(ValueError):
            fail("read", "no_such_stage", "none", "code", "message")
        with self.assertRaises(ValueError):
            fail("read", "observe", "no_such_effect", "code", "message")
        with self.assertRaises(ValueError):
            fail("read", "observe", "none", "", "message")

    def test_vocabulary_is_closed_and_unique(self):
        for vocabulary in (OPERATIONS, STAGES, EFFECTS):
            self.assertEqual(len(vocabulary), len(set(vocabulary)))
            self.assertTrue(all(type(item) is str and item for item in vocabulary))

    def test_fail_keeps_an_explicit_cause(self):
        original = RuntimeError("gdb refused")
        with self.assertRaises(ApiError) as caught:
            fail("execute", "command", "unknown", "command_failed", "command failed", cause=original)
        self.assertIs(caught.exception.__cause__, original)

    def test_fail_without_a_cause_does_not_attach_the_handled_one(self):
        try:
            raise RuntimeError("unrelated")
        except RuntimeError:
            with self.assertRaises(ApiError) as caught:
                fail("execute", "command", "unknown", "command_failed", "command failed")
        self.assertIsNone(caught.exception.__cause__)


if __name__ == "__main__":
    unittest.main()
