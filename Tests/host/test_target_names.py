"""Frame names as GDB reports them after LTO (TC-115); gdb is stubbed, no debugger."""
import importlib
import sys
import types
import unittest
from unittest.mock import patch


class FrameNameTests(unittest.TestCase):
    def test_clone_suffixes_qualifiers_and_parameters_are_removed(self):
        # TC-115: ТЗ 5.10.7
        with patch.dict(sys.modules, {"gdb": types.ModuleType("gdb")}):
            sys.modules.pop("stm32_gdbtest.target", None)
            target = importlib.import_module("stm32_gdbtest.target")
            sys.modules.pop("stm32_gdbtest.target", None)
        name = target.function_name
        for raw, plain in (
                ("HmiManager::init() [clone .constprop.0]", "HmiManager::init"),
                ("ParamRegistry::print() const [clone .constprop.0]", "ParamRegistry::print"),
                ("Print::println(char const*) [clone .constprop.0] [clone .isra.0]", "Print::println"),
                ("SensorManager::init(unsigned long)", "SensorManager::init"),
                ("Foo::operator()(int)", "Foo::operator()"),
                ("main", "main"),
                ("HmiManager::init", "HmiManager::init")):
            with self.subTest(raw=raw):
                self.assertEqual(name(raw), plain)
        self.assertIsNone(name(None))
        self.assertNotEqual(name("HmiManager::init() [clone .constprop.0]"), name("SafetyManager::init"))


if __name__ == "__main__":
    unittest.main()
