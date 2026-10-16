"""QEMU contract: explicit model and options, no accidental hardware route."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stm32_gdbtest import emulators
from stm32_gdbtest.compatibility import runtime_manifest


class QemuTests(unittest.TestCase):
    def document(self, **options):
        return dict(schema=1,emulator=dict(backend='qemu'),qemu=dict(machine='netduinoplus2',**options))

    def load(self, doc=None):
        with patch('stm32_gdbtest.emulators.shutil.which',return_value='qemu-system-arm'):
            return emulators.load(doc or self.document(),'unused.toml')

    def test_commands_and_provenance(self):
        stand=self.load()
        with tempfile.TemporaryDirectory() as directory:
            spec=emulators.server_spec(stand,12345,dict(environment='emulator'),Path(directory))
        self.assertIn('tcp:127.0.0.1:12345',spec['command'])
        self.assertIn('-S',spec['command'])
        self.assertIn('-no-reboot',spec['command'])
        self.assertNotIn('-semihosting-config',spec['command'])
        self.assertIsNone(spec['reset_halt'])
        self.assertIsNone(spec['ready'])
        self.assertEqual(spec['finish'],['disconnect'])
        self.assertNotIn('serial',stand)
        self.assertEqual(emulators.provenance(stand)['gdb_bind_scope'],'127.0.0.1')

    def test_semihosting_opt_in(self):
        spec=emulators.server_spec(self.load(self.document(semihosting=True)),12345,dict(environment='emulator'),Path('.'))
        self.assertIn('enable=on,target=native',spec['command'])
        with self.assertRaises(ValueError):self.load(self.document(semihosting='false'))

    def test_unknown_fields_and_machines_refused(self):
        for key,value in [('machine','netduino2'),('machine','netduinoplus2,accel=kvm'),('args',[]),('keep',True)]:
            doc=self.document();doc['qemu'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.load(doc)
        for key,value in [('startup_timeout_s',True),('startup_timeout_s',0),('shutdown_timeout_s',float('inf')),('keep',True)]:
            doc=self.document();doc['emulator'][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):self.load(doc)
        for key in ('probe','remote','renode'):
            doc=self.document();doc[key]={}
            with self.subTest(key=key),self.assertRaises(ValueError):self.load(doc)

    def test_hardware_and_missing_executable_refused(self):
        with self.assertRaises(ValueError):emulators.server_spec(self.load(),12345,dict(environment='hardware'),Path('.'))
        with patch('stm32_gdbtest.emulators.shutil.which',return_value=None),self.assertRaises(FileNotFoundError):
            emulators.load(self.document(),'unused.toml')

    def test_version_is_evidence_not_hardware_identity(self):
        report=runtime_manifest({'backend':'qemu'},'QEMU emulator version 11.1.0 (custom)')
        self.assertEqual(report['backend']['version'],'11.1.0')
        self.assertIsNone(report['debugger']['firmware'])
