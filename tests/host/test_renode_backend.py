"""Schema 3 and owned Renode configuration: fail before process or target access."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stm32_gdbtest import emulators
from stm32_gdbtest.profile import load_profile, validate_profile

ROOT = Path(__file__).resolve().parents[2]


class RenodeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/'platform.repl').write_text('cpu: CPU.CortexM @ sysbus\n')
        self.document = dict(schema=1, emulator=dict(backend='renode'), renode=dict(platform='platform.repl'))

    def load(self, document=None):
        with patch('stm32_gdbtest.emulators.shutil.which', return_value='renode'):
            return emulators.load(document or self.document, self.root/'stand.toml')

    def test_snapshot_and_generated_script(self):
        stand = self.load()
        (self.root/'platform.repl').write_text('changed')
        profile = load_profile(ROOT/'tests/renode-backend/target.toml')
        spec = emulators.server_spec(stand, 12345, profile, self.root)
        self.assertIn('CPU.CortexM', (self.root/'platform.repl').read_text())
        self.assertIn('StartGdbServer 12345', (self.root/'run.resc').read_text())
        self.assertIsNone(spec['reset_halt'])
        self.assertEqual(spec['finish'], ['disconnect'])
        self.assertNotIn('serial', stand)

    def test_invalid_stands(self):
        variants = [dict(probe={}), dict(remote={}), dict(schema=True)]
        for change in variants:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.load({**self.document, **change})
        for key, value in [('keep',True),('startup_timeout_s',True),('shutdown_timeout_s',0),('startup_timeout_s',float('inf')),('backend','qemu')]:
            d=copy.deepcopy(self.document);d['emulator'][key]=value
            with self.subTest(key=key,value=value), self.assertRaises(ValueError):self.load(d)

    def test_external_model_inputs_refused(self):
        for text in ('using "other.repl"','filename: "other.py"','// https://example.test/model'):
            (self.root/'platform.repl').write_text(text)
            with self.subTest(text=text), self.assertRaises(ValueError):self.load()

    def test_no_executable_and_unsafe_path(self):
        with patch('stm32_gdbtest.emulators.shutil.which', return_value=None), self.assertRaises(FileNotFoundError):
            emulators.load(self.document,self.root/'stand.toml')
        with self.assertRaises(ValueError):emulators.path_argument('bad;quit')

    def test_schema3_hardware_compatibility(self):
        old=load_profile(ROOT/'tests/fixtures/f103c8/target.toml')
        data={k:v for k,v in old.items() if k not in ('reset_halt','reset_run')}
        data.update(schema=3,environment='hardware',architecture='cortex-m')
        self.assertEqual(validate_profile(data)['identity'],old['identity'])
        del data['identity']
        with self.assertRaises(ValueError):validate_profile(data)

    def test_schema3_emulator_restrictions(self):
        data=load_profile(ROOT/'tests/renode-backend/target.toml')
        for change in ({'identity':{'address':0,'mask':1,'value':0}}, {'architecture':'x86'}, {'environment':'unknown'}, {'schema':2}):
            with self.subTest(change=change), self.assertRaises(ValueError):validate_profile({**data,**change})
        with self.assertRaises(ValueError):emulators.server_spec(self.load(),12345,{'environment':'hardware'},self.root)
