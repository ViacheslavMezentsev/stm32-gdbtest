"""Local OpenOCD/J-Link release: finish ordering and bounded process ownership."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from stm32_gdbtest import openocd
from stm32_gdbtest.backends import server_spec
from stm32_gdbtest.processes import spawn_options, stop_tree


class OpenocdShutdownTests(unittest.TestCase):
    def spec(self, **extra):
        stand = dict(backend='openocd', interface='interface/jlink.cfg',
                     executable='openocd', serial='TEST1', speed_khz=1000)
        stand.update(extra)
        return server_spec(stand, 12345, dict(schema=2, openocd_target='target/test.cfg'), Path('.'))

    def test_arm_after_reset_and_only_in_finish(self):
        spec = self.spec()
        self.assertEqual(spec['finish'], ['monitor reset run', openocd.SHUTDOWN_ON_DETACH, 'disconnect'])
        self.assertNotIn('shutdown', ' '.join(spec['command']))

    def test_stlink_and_remote_keep_existing_lifecycle(self):
        for options in ({'interface': 'interface/stlink.cfg'}, {'remote': {'host': 'stand'}}):
            spec = self.spec(**options)
            self.assertEqual(spec['finish'], ['monitor reset run', 'disconnect'])

    def process(self, code):
        p = subprocess.Popen([sys.executable, '-c', code], **spawn_options())
        self.addCleanup(stop_tree, p)
        return p

    def test_delayed_normal_exit_is_not_killed(self):
        p = self.process('import time; time.sleep(0.1)')
        report = {}
        with patch.object(openocd, 'stop_tree') as kill:
            openocd.stop_managed(p, report)
        kill.assert_not_called()
        self.assertEqual(report['server_shutdown']['status'], 'VERIFIED')
        self.assertEqual(report['server_shutdown']['exit_code'], 0)

    def test_nonzero_exit_is_error(self):
        p = self.process('raise SystemExit(7)')
        report = {}
        with self.assertRaises(RuntimeError):
            openocd.stop_managed(p, report)
        self.assertEqual(report['server_shutdown']['exit_code'], 7)
        self.assertEqual(report['server_shutdown']['status'], 'ERROR')

    def test_timeout_reaps_owned_process_and_preserves_verdict(self):
        p = self.process('import time; time.sleep(60)')
        report = {'status': 'FAIL', 'status_before_cleanup': 'FAIL'}
        with patch.object(openocd, 'SHUTDOWN_TIMEOUT_S', 0.1):
            with self.assertRaises(subprocess.TimeoutExpired):
                openocd.stop_managed(p, report)
        self.assertIsNotNone(p.poll())
        self.assertTrue(report['server_shutdown']['forced'])
        self.assertEqual(report['server_shutdown']['status'], 'ERROR')
        self.assertEqual(report['status_before_cleanup'], 'FAIL')

    def test_already_exited_success_is_verified(self):
        p = self.process('pass')
        p.wait(timeout=3)
        report = {}
        openocd.stop_managed(p, report)
        self.assertEqual(report['server_shutdown']['status'], 'VERIFIED')


if __name__ == '__main__':
    unittest.main()
