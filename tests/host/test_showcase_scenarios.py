"""The showcase scenarios: the one source-line location and the shared scenario directory."""
from pathlib import Path
import re
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
        source = (COMMON / "board" / "test_until_target.py").read_text(encoding="utf-8")
        for line in ("app_receiver.c:22", "app_receiver.c:24"):
            self.assertIn(f'= "{line}"', source)

    def test_only_the_until_scenario_names_source_lines(self):
        location = re.compile(r'"[\w./-]+\.[ch]:\d+"')
        named = sorted(path.name for path in ROOT.glob("tests/**/test_*.py")
                       if "build" not in path.parts and "dev-" not in str(path.parent)
                       and path.parent.name == "board" and location.search(path.read_text(encoding="utf-8")))
        self.assertEqual(named, ["test_until_target.py"])

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
