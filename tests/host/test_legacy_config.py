"""Legacy views use real validators and package reader; no MCU/ELF execution."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from stm32_gdbtest.configuration import load_legacy
from stm32_gdbtest.configuration import ConfigError, DEFAULTS, freeze
from stm32_gdbtest.full_image import load_policy
from stm32_gdbtest.profile import load_profile
from stm32_gdbtest.package import pack, open_package
from test_session_config import TARGET, IMAGE


class LegacyConfigTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / 'source'
        board = self.source / 'tests/board'
        board.mkdir(parents=True)
        (board/'test_one.py').write_text('from stm32_gdbtest import test\n'
            '@test("HW_LEGACY")\ndef one(t):\n    pass\n', encoding='utf-8')
        self.profile = self.source/'target.toml'
        self.profile.write_bytes(TARGET.encode())
        self.image = self.source/'policy.toml'
        self.image.write_bytes(IMAGE.encode())
        (self.source/'fw.elf').write_bytes(b'synthetic host fixture, not firmware')
        self.session = dict(root=str(self.source), profile=str(self.profile),
                            tests=str(board), elf=str(self.source/'fw.elf'), gdb='unused')

    def test_defaults_no_discovery_or_fake_source(self):
        (self.source/'session.toml').write_text('invalid TOML [', encoding='utf-8')
        (self.source/'api.toml').write_text('schema=1\n[records]\nmax_records=1', encoding='utf-8')
        snapshot = load_legacy(self.session, environ={})
        self.assertEqual(snapshot.config['target'], freeze(load_profile(self.profile)))
        self.assertEqual(snapshot.config['api']['records'], DEFAULTS)
        self.assertIsNone(snapshot.config['image'])
        self.assertIsNone(snapshot.config_props['image'])
        self.assertIsNone(snapshot.config_props['api'])
        self.assertIsNone(snapshot.session_sha256)
        self.assertEqual(set(snapshot._source_bytes), {'target'})

    def test_cli_precedes_environment_and_invalid_cli_never_falls_back(self):
        environment = {'STM32_GDBTEST_IMAGE_POLICY': str(self.source/'missing.toml')}
        result = load_legacy(self.session, image_policy=self.image, environ=environment)
        policy, sha = load_policy(self.image, load_profile(self.profile))
        self.assertEqual(result.config['image']['image'], policy)
        self.assertEqual(result.config_props['image']['sha256'], sha)
        with self.assertRaises(ConfigError):
            load_legacy(self.session, image_policy=self.source/'missing.toml',
                        environ={'STM32_GDBTEST_IMAGE_POLICY': str(self.image)})

    def test_environment_selection_and_no_internal_override(self):
        snapshot = load_legacy(dict(self.session, image_policy_path='stale.toml'),
                              environ={'STM32_GDBTEST_IMAGE_POLICY': str(self.image)})
        self.assertEqual(snapshot.config_props['image']['reference'], str(self.image))
        self.assertIsNone(load_legacy(dict(self.session, image_policy_path='stale.toml'),
                                     environ={}).config['image'])

    def test_capture_once_hashes_original_and_views_survive_removal(self):
        seen = []
        original = self.profile.read_bytes()
        def reader(path):
            seen.append(path)
            raw = path.read_bytes()
            path.write_bytes(b'changed after capture')
            return raw
        snapshot = load_legacy(self.session, image_policy=self.image, environ={}, reader=reader)
        self.assertEqual(seen, [self.profile.resolve(), self.image.resolve()])
        self.source.rename(self.root/'moved')
        self.assertEqual(snapshot.config_props['target']['sha256'], hashlib.sha256(original).hexdigest())
        self.assertEqual(snapshot.config['target']['mcu'], 'STM32F411CEU6')
        target = snapshot
        with self.assertRaises(TypeError):
            target.config_props['target']['data']['identity']['value'] = 0
        with self.assertRaises(TypeError):
            target.config['target']['core_registers'][0] = 'r0'
        with self.assertRaises(AttributeError):
            target.config_props = {}

    def test_invalid_selected_files_and_wrong_mode(self):
        for raw in (b'not toml [', IMAGE.replace('end=0x08004000', 'end=0x09000000').encode(),
                    (IMAGE+'unknown=1\n').encode()):
            self.image.write_bytes(raw)
            with self.assertRaises(ConfigError):
                load_legacy(self.session, image_policy=self.image, environ={})
        self.profile.write_bytes((TARGET+'\n[unknown]\nx=1\n').encode())
        with self.assertRaises(ConfigError):
            load_legacy(self.session, environ={})
        with self.assertRaises(ConfigError):
            load_legacy(dict(self.session, session_config='session.toml'), environ={})

    def test_old_package_uses_actual_extracted_sources(self):
        output = self.root/'old.zip'
        pack(self.session, output, include=['policy.toml'])
        self.source.rename(self.root/'original-unavailable')
        with patch('stm32_gdbtest.package.find_gdb', return_value='unused'):
            session = open_package(output, self.root/'receiver', 'unused')
        # Inclusion alone does not activate a policy in legacy mode.
        self.assertIsNone(load_legacy(session, environ={}).config['image'])
        selected = Path(session['root'])/'policy.toml'
        snapshot = load_legacy(session, image_policy=selected, environ={})
        self.assertEqual(snapshot.config_props['target']['reference'], session['profile'])
        self.assertEqual(snapshot.config_props['image']['reference'], str(selected))
        for role in ('target', 'image'):
            path = Path(snapshot.config_props[role]['reference'])
            self.assertTrue(path.is_relative_to(Path(session['root'])))
            self.assertEqual(snapshot.config_props[role]['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertIsNone(snapshot.config_props['api'])
        self.assertIsNone(snapshot.session_sha256)
        self.assertEqual(snapshot.config['image']['image']['end'], 0x08004000)
