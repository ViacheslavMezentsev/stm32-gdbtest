"""Journal export contract, independent verdicts and infrastructure reports."""

import hashlib
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
import xml.etree.ElementTree as ET

from stm32_gdbtest.configuration import ConfigError, load_session
from stm32_gdbtest.config_transport import dumps, loads
from stm32_gdbtest.result_capture import save, read, finalize
from stm32_gdbtest.reports import write_reports
from test_session_config import TARGET


class CaptureTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.report = dict(id='HW_SAMPLE', run_id='unique-run', status='PASS', duration_s=0, mode='hardware')
        self.target = Mock()
        self.target.records.return_value = [dict(sequence=1, name='sample', data={'value': 3.2, 'missing': None})]

    def test_configuration_and_capsule(self):
        (self.root / 'target.toml').write_text(TARGET)
        path = self.root / 'session.toml'
        for suffix, expected in [('', False), ('\n[results]\ncapture=true', True),
                                 ('\n[results]\ncapture=false', False)]:
            path.write_text('[config]\ntarget="target.toml"' + suffix)
            config = load_session(path)
            self.assertEqual(config.capture_results, expected)
            self.assertEqual(loads(dumps(config)).capture_results, expected)
        for text in ['capture=1', 'capture="true"', 'other=true']:
            path.write_text('[config]\ntarget="target.toml"\n[results]\n' + text)
            with self.assertRaises(ConfigError):
                load_session(path)

    def test_verdict_matrix_and_junit(self):
        for status, code in [('PASS', 0), ('FAIL', 1), ('ERROR', 2)]:
            for outcome in ['disabled', 'saved', 'error', 'unavailable']:
                with self.subTest(status=status, capture=outcome):
                    (self.root / 'records.json').unlink(missing_ok=True)
                    report = dict(self.report, status=status, error='original diagnostic')
                    self.target.records.side_effect = OSError('disk refused') if outcome == 'error' else None
                    if outcome in ('saved', 'error'):
                        save(self.root, report, self.target, 'normal' if status == 'PASS' else 'interrupted')
                    finalize(self.root, report, outcome != 'disabled')
                    failed = outcome in ('error', 'unavailable')
                    self.assertEqual(report['command_code'], 2 if failed else code)
                    self.assertEqual(report['status'], status)
                    self.assertEqual(report['error'], 'original diagnostic')
                    write_reports(self.root, report)
                    suite = ET.parse(self.root / 'junit.xml').getroot()
                    self.assertEqual(int(suite.get('tests')), 1 + failed)
                    self.assertEqual(int(suite.get('errors')), (status == 'ERROR') + failed)
                    self.assertEqual(int(suite.get('failures')), status == 'FAIL')
                    self.assertEqual(len(suite.findall('testcase')), 1 + failed)

    def test_snapshot_and_tampering(self):
        save(self.root, self.report, self.target, 'normal')
        self.assertEqual(read(self.root, self.report)['records'], self.target.records())
        path = self.root / 'records.json'
        original = path.read_bytes()
        for field, value in [('run_id', 'other'), ('case_id', 'other'), ('schema', True),
                             ('records', [dict(sequence=True, name='sample', data=0)])]:
            snapshot = json.loads(original)
            snapshot[field] = value
            raw = json.dumps(snapshot).encode()
            path.write_bytes(raw)
            report = dict(self.report, capture=dict(self.report['capture'], sha256=hashlib.sha256(raw).hexdigest()))
            with self.assertRaises(ValueError):
                read(self.root, report)
        path.write_bytes(original + b' ')
        finalize(self.root, self.report, True)
        self.assertEqual(self.report['command_code'], 2)
        self.assertEqual(self.report['capture']['status'], 'error')

    def test_missing_target_prepare_and_existing_file(self):
        save(self.root, self.report, None, 'unknown')
        self.assertFalse((self.root / 'records.json').exists())
        finalize(self.root, self.report, True)
        self.assertEqual(self.report['capture']['status'], 'unavailable')
        report = dict(self.report, mode='prepare')
        finalize(self.root, report, True)
        self.assertEqual(report['command_code'], 0)
        path = self.root / 'records.json'
        path.write_text('preserved')
        save(self.root, self.report, self.target, 'normal')
        self.assertEqual(path.read_text(), 'preserved')
        self.assertEqual(self.report['capture']['status'], 'error')

    def test_runner_console_and_timeout_without_journal(self):
        from stm32_gdbtest.runner import run
        (self.root / 'target.toml').write_text(TARGET)
        config = self.root / 'session.toml'
        config.write_text('[config]\ntarget="target.toml"\n[results]\ncapture=true')
        session = dict(root=str(self.root), out=str(self.root / 'runs'),
                       profile=str(self.root / 'target.toml'), session_config=str(config), stand='fixture')
        test = dict(id='HW_SAMPLE', timeout_s=2)
        for timeout in (False, True):
            def execute(session, test, stand, out, report, limit, profile):
                if timeout:
                    raise TimeoutError('GDB timeout')
                report.update(status='FAIL', error='original check')
                report['capture'] = dict(status='error', completion='interrupted',
                                         error=dict(type='OSError', message='disk refused'))

            output = io.StringIO()
            with patch('stm32_gdbtest.runner.load_stand', return_value=dict(backend='openocd', serial='fixture')), \
                    patch('stm32_gdbtest.runner.probe_lock', return_value=contextlib.nullcontext()), \
                    patch('stm32_gdbtest.runner.execute', side_effect=execute), contextlib.redirect_stdout(output):
                self.assertEqual(run(session, test), 2)
            text = output.getvalue()
            self.assertIn('Command: ERROR (2)', text)
            self.assertIn('Scenario: ERROR' if timeout else 'Scenario: FAIL', text)
            self.assertIn('GDB timeout' if timeout else 'original check', text)
            self.assertIn('Capture: UNAVAILABLE' if timeout else 'Capture: ERROR', text)
            self.assertFalse(list((self.root / 'runs').glob('*/records.json')))
