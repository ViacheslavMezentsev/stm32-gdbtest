"""Legacy configuration tests in GDB Python; never connects to an MCU."""
import hashlib
import io
import json
from pathlib import Path
import platform
import unittest


def run(output):
    import gdb
    suite = unittest.TestLoader().loadTestsFromName('test_legacy_config')
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = {'schema': 1, 'hardware': False, 'synthetic_elf': True,
              'gdb': gdb.VERSION, 'python': platform.python_version(),
              'tests': result.testsRun, 'failures': len(result.failures),
              'errors': len(result.errors), 'skipped': len(result.skipped),
              'status': 'PASS' if result.wasSuccessful() else 'ERROR',
              'loader_sha256': hashlib.sha256(Path(__file__).with_name('legacy_config.py').read_bytes()).hexdigest(),
              'log': log.getvalue()}
    Path(output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not result.wasSuccessful():
        raise RuntimeError('legacy configuration suite failed; inspect result JSON')
