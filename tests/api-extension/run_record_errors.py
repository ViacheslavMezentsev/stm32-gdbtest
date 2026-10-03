"""Run record contracts inside GDB Python without connecting to a target."""
import hashlib
import io
import json
from pathlib import Path
import platform
import unittest


def run(output):
    import gdb
    suite = unittest.TestLoader().loadTestsFromNames(['test_record', 'test_record_errors'])
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report = {'schema': 1, 'hardware': False, 'gdb': gdb.VERSION,
              'python': platform.python_version(), 'tests': result.testsRun,
              'failures': len(result.failures), 'errors': len(result.errors),
              'skipped': len(result.skipped),
              'status': 'PASS' if result.wasSuccessful() else 'ERROR',
              'journal_sha256': hashlib.sha256(Path(__file__).with_name('evidence.py').read_bytes()).hexdigest(),
              'log': log.getvalue()}
    Path(output).write_text(json.dumps(report, indent=2), encoding='utf-8')
    if not result.wasSuccessful():
        raise RuntimeError('record contract suite failed; inspect result JSON')
