"""Run isolated example helpers without importing GDB or touching hardware."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / 'tests/live-observer'


class LiveObserverExample(unittest.TestCase):
    def test_recovery_and_admission(self):
        for script in ('test_recovery.py', 'test_owned_recovery.py', 'test_contract.py', 'fpb_adapter_host.py'):
            with self.subTest(script=script):
                result = subprocess.run([sys.executable, '-B', str(EXAMPLE / script)], cwd=ROOT,
                                        capture_output=True, text=True, timeout=60)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
