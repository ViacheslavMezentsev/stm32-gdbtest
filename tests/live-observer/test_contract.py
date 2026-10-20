"""Offline acceptance: no process/socket on a missing or default hardware admission."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import campaign
from policy import layout, can_restore, evidence
from run import assess
from sealed import validate


class Contract(unittest.TestCase):
    def invoke(self, extra=(), serial='TESTSERIAL'):
        args = ['campaign', '--package', 'unused', '--stand', 'unused', '--serial', serial, *extra]
        manifest = dict(cases=[], files={'neutral.elf': 'hash'})
        stand = dict(backend='openocd', serial='TESTSERIAL', interface='interface/stlink.cfg')
        with patch.object(sys, 'argv', args), patch('campaign.validate', return_value=manifest), \
             patch('stm32_gdbtest.backends.load_stand', return_value=stand), \
             patch('campaign.server_commands', return_value={'command': ['openocd']}), \
             patch('subprocess.Popen', side_effect=AssertionError('process forbidden')), \
             patch('socket.socket', side_effect=AssertionError('socket forbidden')), \
             contextlib.redirect_stdout(io.StringIO()):
            campaign.main()

    def test_default_plan(self):
        self.invoke()

    def test_wrong_serial(self):
        with self.assertRaises(ValueError):
            self.invoke(serial='OTHER')

    def test_missing_admission(self):
        with self.assertRaises(ValueError):
            self.invoke(['--allow-hardware', 'f411ce'])

    def test_recovery_requires_admission(self):
        with self.assertRaises(ValueError):
            self.invoke(['--allow-hardware', 'f411ce', '--recover', 'missing'])

    def test_layout_and_quiescence(self):
        self.assertEqual(layout(0x20008000, 4096, 512)['vectors'], 0x20008800)
        for args in ((0x20008004, 4096, 512), (0x20008000, 4095, 512), (0x20008000, 4096, 128)):
            with self.assertRaises(ValueError):
                layout(*args)
        for args in ((1, 0), (0, 1)):
            with self.assertRaises(RuntimeError):
                can_restore(*args)
        self.assertEqual(evidence(0, 0, 0), 'CONFIRMED')
        self.assertEqual(evidence(0, 0, 0, complete=False), 'UNKNOWN')

    def test_expected_error_requires_cause_and_cleanup(self):
        result = dict(status='ERROR', error='intentional before resume', cleanup='VERIFIED')
        records = [dict(name='observer_cleanup', data={'status': 'VERIFIED'})]
        self.assertTrue(assess('HW_OBSERVER_EXCEPTION', result, records, 2)['ok'])
        for changes in (dict(error='connection failed'), dict(cleanup='ERROR'), dict(teardown_error='lost')):
            self.assertFalse(assess('HW_OBSERVER_EXCEPTION', dict(result, **changes), records, 2)['ok'])
        self.assertFalse(assess('HW_OBSERVER_EXCEPTION', result, [], 2)['ok'])

    def test_hardware_result_uses_execution_cleanup(self):
        records = [dict(name='observer_cleanup', data={'status': 'VERIFIED'})]
        result = dict(status='PASS', execution_cleanup='VERIFIED', image_verified=True, teardown='reset_run')
        self.assertTrue(assess('HW_OBSERVER_BASELINE', result, records, 0, 'hardware')['ok'])
        self.assertFalse(assess('HW_OBSERVER_BASELINE', result, records, 0)['ok'])
        for changes in (dict(execution_cleanup='ERROR'), dict(image_verified=False), dict(teardown='disconnected'),
                        dict(teardown_error='lost')):
            self.assertFalse(assess('HW_OBSERVER_BASELINE', dict(result, **changes), records, 0, 'hardware')['ok'])
        error = dict(result, status='ERROR', error='intentional before resume')
        self.assertTrue(assess('HW_OBSERVER_EXCEPTION', error, records, 2, 'hardware')['ok'])

    def test_negative_is_specific(self):
        result = dict(status='FAIL', cleanup='VERIFIED', checks=[dict(name='ISR count', passed=False)])
        records = [dict(name='observer_cleanup', data={'status': 'VERIFIED'})]
        self.assertTrue(assess('HW_OBSERVER_NEGATIVE', result, records, 1)['ok'])
        result['checks'][0]['name'] = 'unrelated failure'
        self.assertFalse(assess('HW_OBSERVER_NEGATIVE', result, records, 1)['ok'])

    def test_reviewed_map_anchors(self):
        from tools.ddtt_guard import validate_point
        root = Path(__file__).resolve().parents[2]
        mapping = json.loads((Path(__file__).parent / 'map.template.json').read_text())
        self.assertEqual(mapping['environment'], 'emulator')
        self.assertEqual(len(mapping['points']), 3)
        for point in mapping['points']:
            self.assertGreater(validate_point(root, point), 0)
            self.assertEqual(point['scenario'], 'HW_OBSERVER_SEVEN')

    def test_seal_rejects_traversal_before_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'manifest.json').write_text(json.dumps({'files': {'../outside': 'hash'}}))
            with self.assertRaisesRegex(ValueError, 'nonlocal'):
                validate(path)


if __name__ == '__main__':
    unittest.main()
