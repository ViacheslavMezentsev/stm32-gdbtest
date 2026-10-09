import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PublicApiTests(unittest.TestCase):
    def test_host_import_does_not_require_gdb(self):
        result = subprocess.run([sys.executable, "-B", "-c",
            "import sys, stm32_gdbtest as api; "
            "assert issubclass(api.RecordError, ValueError); assert 'gdb' not in sys.modules; assert api.API_VERSION == 2; "
            "f = lambda target: None; assert api.case('HW_EXAMPLE')(f) is f"],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_module_cli_version_and_collection(self):
        result = subprocess.run([sys.executable, "-B", "-m", "stm32_gdbtest", "--version"],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "stm32-gdbtest 0.3.0")
        result = subprocess.run([sys.executable, "-B", "-m", "stm32_gdbtest", "collect",
            "--tests", "examples/minimal-consumer/profile/tests/board"],
            cwd=ROOT, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)[0]["id"], "HW_CONSUMER_GPIO")
