"""TC-149/150: packaged configuration remains usable without original sources."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

from stm32_gdbtest.configuration import capture, ConfigError
from stm32_gdbtest.config_transport import dumps, loads
from stm32_gdbtest.package import pack, open_package
from stm32_gdbtest.runner import run
from test_session_config import TARGET, IMAGE


class SessionPackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        board = self.source / 'tests' / 'board'
        board.mkdir(parents=True)
        (board / 'test_sample.py').write_text('from stm32_gdbtest import case\n'
            '@case("HW_SAMPLE")\ndef sample(t):\n    pass\n', encoding='utf-8')
        for name, text in {'target.toml': TARGET, 'image.toml': IMAGE,
            'api.toml': 'schema=1\n[records]\nmax_records=3\n[custom]\ndate=2026-10-03\n',
            'session.toml': '[config]\ntarget="target.toml"\napi="api.toml"\nimage="image.toml"'}.items():
            (self.source/name).write_text(text, encoding='utf-8')
        (self.source/'firmware.elf').write_bytes(b'host fixture')
        self.session = dict(root=str(self.source), tests=str(board),
            profile=str(self.source/'target.toml'), session_config=str(self.source/'session.toml'),
            elf=str(self.source/'firmware.elf'), gdb='unused', out=str(self.source/'runs'))

    def test_package_uses_captured_bytes_and_receiver_needs_no_sources(self):
        with patch.dict(os.environ, {}, clear=True):
            self.session['_config_capsule'] = dumps(capture(self.session))
            (self.source/'target.toml').write_text('corrupted after capture', encoding='utf-8')
            (self.source/'api.toml').write_text('corrupted after capture', encoding='utf-8')
            archive = self.root/'prepared.zip'
            manifest = pack(self.session, archive, include=['api.toml'])
            with zipfile.ZipFile(archive) as bundle:
                self.assertIn(b'max_records=3', bundle.read('api.toml'))
            self.source.rename(self.root/'moved')
            with patch('stm32_gdbtest.package.find_gdb', return_value='unused'):
                received = open_package(archive, self.root/'receiver')
            config = capture(received)
        self.assertEqual(config.config['api']['records']['max_records'], 3)
        self.assertEqual(config.config['api']['custom']['date'].isoformat(), '2026-10-03')
        self.assertEqual(config.config_props['api']['reference'], 'api.toml')
        self.assertEqual(config.config_props['target']['sha256'], manifest['files']['profile/target.toml'])
        with self.assertRaises(ConfigError):
            capture(received, image_policy='image.toml', environ={})

    def test_legacy_transport_preserves_real_sources_without_session(self):
        legacy = dict(self.session)
        del legacy['session_config']
        config = capture(legacy, image_policy=self.source/'image.toml', environ={})
        encoded = dumps(config)
        self.source.rename(self.root/'gone')
        restored = loads(encoded)
        self.assertIsNone(restored.session_sha256)
        self.assertIsNone(restored.config_props['api'])
        self.assertEqual(restored.config_props, config.config_props)
        self.assertEqual(restored.config, config.config)

    def test_stale_selection_and_invalid_api_fail_before_tools_or_lock(self):
        for kind in ('profile', 'limit', 'override'):
            session = dict(self.session)
            (self.source/'api.toml').write_text('schema=1\n[records]\nmax_records=3', encoding='utf-8')
            if kind == 'profile':
                session['profile'] = str(self.source/'other.toml')
            if kind == 'limit':
                (self.source/'api.toml').write_text('schema=1\n[records]\nmax_records=1025', encoding='utf-8')
            with self.subTest(kind=kind), patch.dict(os.environ, {}, clear=True), \
                    patch('stm32_gdbtest.runner.execute') as execute, \
                    patch('stm32_gdbtest.runner.probe_lock') as lock:
                self.assertEqual(run(session, dict(id='HW_SAMPLE', timeout_s=5), prepare_only=True,
                    image_policy='unused' if kind == 'override' else None), 2)
                execute.assert_not_called()
                lock.assert_not_called()
