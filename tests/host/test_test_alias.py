"""The @test alias: identical metadata, exported name and accepted by the collector."""
import tempfile
import unittest
from pathlib import Path

import stm32_gdbtest
from stm32_gdbtest import case, test
from stm32_gdbtest.collect import collect


class AliasedScenario:
    pass


class TestAliasTests(unittest.TestCase):
    def test_alias_is_exported(self):
        self.assertIn("test", stm32_gdbtest.__all__)
        self.assertTrue(callable(stm32_gdbtest.test))
        self.assertTrue(callable(case))

    def test_alias_returns_the_function_unchanged(self):
        def scenario(target):
            return target

        self.assertIs(test("HW_ALIAS_PROBE")(scenario), scenario)
        self.assertIs(case("HW_ALIAS_PROBE")(scenario), scenario)

    def test_alias_accepts_the_same_metadata(self):
        decorated = test("HW_ALIAS_PROBE", timeout_s=45, labels=("api",),
                         contracts=("ci_app_api",))(lambda target: None)
        self.assertTrue(callable(decorated))

    def test_collector_reads_both_decorators(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "test_alias.py").write_text(
                'from stm32_gdbtest import case, test\n\n\n'
                '@test("HW_ALIAS_ONE", timeout_s=30, labels=("a",), contracts=("ci_app_api",))\n'
                'def first(target):\n'
                '    return None\n\n\n'
                '@case("HW_ALIAS_TWO")\n'
                'def second(target):\n'
                '    return None\n', encoding="utf-8")
            collected = collect(directory)
        by_id = {entry["id"]: entry for entry in collected}
        self.assertEqual(sorted(by_id), ["HW_ALIAS_ONE", "HW_ALIAS_TWO"])
        self.assertEqual(by_id["HW_ALIAS_ONE"]["timeout_s"], 30)
        self.assertEqual(by_id["HW_ALIAS_ONE"]["labels"], ["a"])
        self.assertEqual(by_id["HW_ALIAS_ONE"]["contracts"], ["ci_app_api"])
        self.assertEqual(by_id["HW_ALIAS_TWO"]["timeout_s"], 20)

    def test_collector_rejects_a_bad_alias_id(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "test_bad.py").write_text(
                'from stm32_gdbtest import test\n\n\n'
                '@test("not-a-case-id")\n'
                'def scenario(target):\n'
                '    return None\n', encoding="utf-8")
            with self.assertRaises(ValueError) as caught:
                collect(directory)
        self.assertIn("Invalid case ID", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
