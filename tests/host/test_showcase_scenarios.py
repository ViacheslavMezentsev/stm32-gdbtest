"""The showcase scenarios rely on fixture source lines and on the shared scenario directory."""
from pathlib import Path
import unittest

from stm32_gdbtest.collect import collect, trace

ROOT = Path(__file__).resolve().parents[2]
COMMON = ROOT / "tests/firmware/common/tests"
SHOWCASE = {"HW_CI_INJECT_ZERO", "HW_CI_WHO_WRITES", "HW_CI_RETURN_VALUE", "HW_CI_CONDITIONAL_STOP",
            "HW_CI_STEP_SOURCE", "HW_CI_UNTIL_TARGET", "HW_CI_POINT_BUDGET", "HW_CI_PROFILE",
            "HW_CI_CALL_PREDICATE"}


class ShowcaseTests(unittest.TestCase):
    def test_receiver_lines_named_by_the_scenarios(self):
        lines = (ROOT / "tests/firmware/src/app_receiver.c").read_text(encoding="utf-8").splitlines()
        self.assertIn("app_received.calls++;", lines[22 - 1])
        self.assertIn("app_state                     = next;", lines[24 - 1])
        for name in ("test_inject_zero.py", "test_until_target.py", "test_return_value.py"):
            source = (COMMON / "board" / name).read_text(encoding="utf-8")
            for line in ("app_receiver.c:22", "app_receiver.c:24"):
                if line in source:
                    self.assertIn(f'= "{line}"', source)

    def test_showcase_is_collected_and_traced_once(self):
        tests = collect(COMMON / "board")
        self.assertLessEqual(SHOWCASE, {test["id"] for test in tests})
        trace(tests, COMMON / "requirements.md")
        for test in tests:
            if test["id"] in SHOWCASE:
                self.assertIn("showcase" if test["id"] != "HW_CI_PROFILE" else "profile", test["labels"])
                self.assertEqual(test["contracts"], ["ci_app_api"])


if __name__ == "__main__":
    unittest.main()
