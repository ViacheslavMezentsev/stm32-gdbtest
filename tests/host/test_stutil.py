"""st-util dialect, ownership, remote configuration and runtime evidence (TC-168)."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from stm32_gdbtest import backends, doctor, probes, processes, remote
from stm32_gdbtest.compatibility import runtime_manifest
from stm32_gdbtest.profile import load_profile, validate_profile

ROOT = Path(__file__).resolve().parents[2]
SERIAL = "0123456789abcdef01234567"
PROFILE = load_profile(ROOT / "tests/firmware/profiles/f030r8/target.toml")


class StUtilTests(unittest.TestCase):
    def load(self, extra="", remote_table=""):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stand.toml"
            path.write_text(f'[probe]\nbackend="st-util"\nserial="{SERIAL}"\n' + extra + remote_table)
            with patch("stm32_gdbtest.backends.shutil.which", return_value="/bin/st-util"):
                return backends.load_stand(path)

    def test_local_stand_needs_no_programmer(self):
        stand = self.load()
        self.assertEqual(stand['backend'], 'st-util')
        self.assertEqual(stand['speed_khz'], 1000)
        self.assertNotIn('programmer_dir', stand)

    def test_rejects_foreign_options_and_invalid_serial_speed(self):
        for extra in ('programmer_dir="/ST"\n', 'interface="SWD"\n', 'shared=true\n',
                      'speed_khz=true\n', 'speed_khz=0\n', 'speed_khz=4001\n'):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                self.load(extra)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'stand.toml'
            for serial in ('ABC123', 'G' * 24):
                path.write_text(f'[probe]\nbackend="st-util"\nserial="{serial}"\n')
                with self.assertRaisesRegex(ValueError, '24-digit'):
                    backends.load_stand(path)

    def test_remote_default_and_forwarded_port(self):
        stand = self.load(remote_table='[remote]\nhost="stand"\n')
        self.assertEqual(stand['executable'], 'st-util')
        spec = backends.server_spec(stand, '{port}', PROFILE, Path('/out'))
        config = remote.serve_config(processes.probe_identity(SERIAL, 'st-util'), 62001, spec['command'])
        self.assertIn('62001', str(config))
        self.assertEqual(spec['ready'], 'Listening at *:{port}')

    def test_serial_frequency_and_teardown_dialect(self):
        spec = backends.server_spec(self.load(), 62001, PROFILE, Path('/out'))
        command = spec['command']
        self.assertEqual(command[command.index('--serial') + 1], SERIAL.upper())
        self.assertEqual(command[command.index('--freq') + 1], '1000k')
        self.assertIn('--multi', command)
        self.assertIn('--no-reset', command)
        self.assertNotIn('--remote', command)
        self.assertEqual(spec['reset_halt'], 'monitor reset')
        self.assertEqual(spec['setup'], ['set mem inaccessible-by-default off'])
        self.assertEqual(spec['finish'], ['monitor reset', 'monitor resume', 'disconnect'])

    def test_schema2_accepts_only_stutil_reset(self):
        for section in ({}, {'reset_halt': 'monitor reset'}):
            profile = validate_profile(dict(PROFILE, **{'st-util': section}))
            self.assertEqual(probes.dialect(profile, 'st-util'), ('monitor reset', []))
        for section in ({'reset_halt': 'monitor reset halt'}, {'reset_run': 'monitor resume'},
                        {'command': 'monitor reset'}, 'monitor reset'):
            with self.subTest(section=section), self.assertRaises(ValueError):
                validate_profile(dict(PROFILE, **{'st-util': section}))

    def test_schema1_openocd_commands_do_not_leak(self):
        profile = {k: v for k, v in PROFILE.items() if k not in probes.BACKEND_SECTIONS}
        profile.update(schema=1, reset_halt='monitor reset init', reset_run='monitor reset run')
        self.assertEqual(probes.dialect(validate_profile(profile), 'st-util'), ('monitor reset', []))

    def test_override_does_not_replace_recovery(self):
        with patch.dict(os.environ, STM32_GDBTEST_RESET_COMMAND='monitor halt'):
            spec = backends.server_spec(self.load(), 62001, PROFILE, Path('/out'))
        self.assertEqual(spec['reset_halt'], 'monitor halt')
        self.assertEqual(spec['finish'], ['monitor reset', 'monitor resume', 'disconnect'])

    def test_same_probe_lock_for_all_stlink_servers(self):
        stand = self.load()
        self.assertEqual(probes.family(stand), 'stlink')
        identities = {processes.probe_identity(SERIAL, b) for b in ('openocd', 'stlink', 'st-util')}
        self.assertEqual(len(identities), 1)
        with tempfile.TemporaryDirectory() as tmp, processes.probe_lock(Path(tmp), SERIAL, 'st-util'):
            with self.assertRaises(RuntimeError):
                with processes.probe_lock(Path(tmp), SERIAL, 'openocd'):
                    self.fail('overlapping probe ownership')

    def test_runtime_banner_does_not_invent_firmware(self):
        manifest = runtime_manifest({'backend': 'st-util'}, 'st-util 1.9.0\nListening at *:62001...\n')
        self.assertEqual(manifest['backend']['version'], '1.9.0')
        self.assertIsNone(manifest['debugger']['firmware'])
        self.assertIsNone(manifest['debugger']['api'])
        self.assertIsNone(runtime_manifest({'backend': 'st-util'}, '')['backend']['version'])

    def test_doctor_checks_version_without_opening_target(self):
        calls = []
        def output(args, **kwargs):
            calls.append(args)
            return (0, 'v1.9.0')
        with patch('stm32_gdbtest.doctor.find_gdb', return_value=None), \
                patch('stm32_gdbtest.doctor.shutil.which', return_value=None), \
                patch('stm32_gdbtest.doctor.backends.load_stand', return_value={
                    'backend': 'st-util', 'executable': 'st-util', 'serial': SERIAL, 'remote': None}), \
                patch('stm32_gdbtest.doctor._output', side_effect=output):
            result = doctor.diagnose(stand='unused')
        self.assertEqual(calls, [['st-util', '--version']])
        self.assertIn({'name': 'st-util', 'status': 'OK', 'detail': 'v1.9.0'}, result)


if __name__ == '__main__':
    unittest.main()
