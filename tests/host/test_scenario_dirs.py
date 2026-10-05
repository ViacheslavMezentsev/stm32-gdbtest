"""Several scenario directories: collection order, duplicate IDs, requirements and contract registries."""
import json
from pathlib import Path
import tempfile
import unittest

from stm32_gdbtest.collect import collect, scenario_dirs, trace
from stm32_gdbtest.contracts import select_contracts_from

CONTRACT = {"type_context": "app_step", "functions": {"app_step": {"returns": "void", "arguments": []}}}


class ScenarioDirsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.profile = self.root / "profile"
        self.common = self.root / "common"
        for directory in (self.profile, self.common):
            (directory / "board").mkdir(parents=True)

    def scenario(self, directory, name, identifier, contracts=()):
        (directory / "board" / f"test_{name}.py").write_text(
            f'@case("{identifier}", contracts={tuple(contracts)!r})\ndef {name}(t): pass\n')

    def test_collect_keeps_directory_order_and_rejects_duplicates(self):
        self.scenario(self.profile, "adc", "HW_ADC")
        self.scenario(self.common, "read", "HW_READ")
        tests = collect([self.profile / "board", self.common / "board"])
        self.assertEqual([test["id"] for test in tests], ["HW_ADC", "HW_READ"])
        self.assertEqual(collect(str(self.profile / "board"))[0]["id"], "HW_ADC")
        self.scenario(self.common, "adc_copy", "HW_ADC")
        with self.assertRaisesRegex(ValueError, "Duplicate case ID: HW_ADC"):
            collect([self.profile / "board", self.common / "board"])

    def test_scenario_dirs_of_a_session(self):
        self.assertEqual(scenario_dirs({"tests": "a"}), ["a"])
        self.assertEqual(scenario_dirs({"tests": "a", "test_dirs": ["b", "c"]}), ["a", "b", "c"])

    def test_trace_joins_requirements_of_every_directory(self):
        self.scenario(self.profile, "adc", "HW_ADC")
        self.scenario(self.common, "read", "HW_READ")
        (self.profile / "requirements.md").write_text("## HW_ADC\ntext\n")
        (self.common / "requirements.md").write_text("## HW_READ\ntext\n")
        tests = collect([self.profile / "board", self.common / "board"])
        trace(tests, [self.profile / "requirements.md", self.common / "requirements.md"])
        with self.assertRaisesRegex(ValueError, "Missing tests"):
            trace(tests, self.profile / "requirements.md")
        (self.common / "requirements.md").write_text("## HW_READ\n## HW_ADC\n")
        with self.assertRaisesRegex(ValueError, "Duplicate requirement IDs"):
            trace(tests, [self.profile / "requirements.md", self.common / "requirements.md"])

    def registry(self, directory, names):
        path = directory / "contracts.json"
        path.write_text(json.dumps({"schema": 1, "contracts": {name: dict(CONTRACT) for name in names}}))
        return path

    def test_first_registry_defining_a_contract_wins(self):
        profile = self.registry(self.profile, ["device"])
        common = self.registry(self.common, ["device", "app"])
        selected = select_contracts_from([profile, common], ["app", "device"], None)
        self.assertEqual(list(selected["contracts"]), ["app", "device"])
        self.assertEqual(set(selected["registries"]), {str(profile), str(common)})
        self.assertNotIn("registry_sha256", selected)
        single = select_contracts_from([profile, common], ["device"], None)
        self.assertEqual(single["registries"], {str(profile): single["registry_sha256"]})
        self.assertEqual(select_contracts_from([], [], None), {"schema": 1, "contracts": {}})
        with self.assertRaises(KeyError):
            select_contracts_from([profile, common], ["typo"], None)
        with self.assertRaises(FileNotFoundError):
            select_contracts_from([self.root / "absent.json"], ["app"], None)


if __name__ == "__main__":
    unittest.main()
