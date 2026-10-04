"""Read-only settings and sources views, including their 0.2.x aliases."""
import importlib
import sys
import types
import unittest
from unittest.mock import Mock, patch

from stm32_gdbtest.configuration import DEFAULTS, Configuration, freeze

VIRTUAL = dict(target={}, image=None,
               api=dict(schema=1, records={**DEFAULTS, 'custom': 999}, user=dict(count=3)))


class SettingsTests(unittest.TestCase):
    def setUp(self):
        self.gdb = types.SimpleNamespace(
            error=RuntimeError,
            events=types.SimpleNamespace(stop=Mock()),
            parse_and_eval=lambda expression: types.SimpleNamespace(
                is_optimized_out=False, fetch_lazy=lambda: None, __int__=lambda self: 0),
        )

    def target(self, props=None):
        import builtins
        real_import = builtins.__import__

        def importing_gdb(name, *arguments, **options):
            if name == "gdb":
                return self.gdb
            return real_import(name, *arguments, **options)

        saved = {name: sys.modules.pop(name, None)
                 for name in ("stm32_gdbtest.target", "stm32_gdbtest.values")}
        with patch.object(builtins, "__import__", side_effect=importing_gdb):
            module = importlib.import_module("stm32_gdbtest.target")
        for name, previous in saved.items():
            sys.modules.pop(name, None)
            if previous is not None:
                sys.modules[name] = previous
        configuration = Configuration(
            freeze(VIRTUAL),
            freeze(props if props is not None else dict(target=None, api=None, image=None)), None, {})
        return module.Target({"checks": []}, {"breakpoint_limit": 4, "fault_handlers": []},
                             configuration)

    def test_settings_is_the_read_only_config(self):
        target = self.target()
        self.assertIs(target.settings, target.config)
        self.assertEqual(target.settings["api"]["schema"], 1)
        self.assertEqual(target.settings["api"]["user"]["count"], 3)
        with self.assertRaises(TypeError):
            target.settings["api"] = {}

    def test_settings_nested_values_are_read_only(self):
        target = self.target()
        nested = target.settings["api"]["records"]
        self.assertEqual(nested["max_records"], DEFAULTS["max_records"])
        with self.assertRaises(TypeError):
            nested["max_records"] = 1

    def test_sources_is_the_read_only_provenance(self):
        props = dict(target=None,
                     api=dict(sha256="a" * 64, reference="api.toml", data=dict(schema=1)),
                     image=None)
        target = self.target(props)
        self.assertIs(target.sources, target.config_props)
        self.assertEqual(target.sources["api"]["sha256"], "a" * 64)
        self.assertEqual(target.sources["api"]["reference"], "api.toml")
        with self.assertRaises(TypeError):
            target.sources["api"]["reference"] = "other.toml"

    def test_missing_source_is_reported_as_none(self):
        target = self.target()
        self.assertIsNone(target.sources["api"])
        self.assertIsNone(target.sources["image"])


if __name__ == "__main__":
    unittest.main()
