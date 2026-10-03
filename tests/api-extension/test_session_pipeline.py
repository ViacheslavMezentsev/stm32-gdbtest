"""Host pipeline boundary tests; synthetic ELF never claimed as firmware PASS."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from session_pipeline import ConfiguredTarget, open_configured, prepare_and_pack
from stm32_gdbtest.package import MANIFEST
from test_session_config import TARGET


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "source"
        board = self.source / "profile/tests/board"
        board.mkdir(parents=True)
        (board / "test_one.py").write_text('from stm32_gdbtest import case\n'
            '@case("HW_CONFIG")\ndef config(t):\n    pass\n', encoding="utf-8")
        (self.source / "profile/target.toml").write_bytes(TARGET.encode())
        (self.source / "api.toml").write_text('schema=1\n[custom]\nvalue=42', encoding="utf-8")
        (self.source / "session.toml").write_text(
            '[config]\ntarget="profile/target.toml"\napi="api.toml"', encoding="utf-8")
        (self.source / "fw.elf").write_bytes(b"synthetic host-only ELF fixture")
        manifest = dict(schema=1, elf_sha256=hashlib.sha256((self.source / "fw.elf").read_bytes()).hexdigest(),
                        profile_sha256=hashlib.sha256(TARGET.encode()).hexdigest(),
                        compilers=[{}], units=[{}], inputs=[{}], library_versions=[], cube_packages=[])
        (self.source / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.session = dict(root=str(self.source), tests=str(board), elf=str(self.source / "fw.elf"),
                            profile=str(self.source / "profile/target.toml"),
                            session_config=str(self.source / "session.toml"),
                            build_manifest=str(self.source / "manifest.json"), gdb="unused")
        self.output = self.root / "out/package.zip"

    def test_package_read_views_and_delegation_after_sources_moved(self):
        prepare_and_pack(self.session, self.output, ['HW_CONFIG'], preflight=lambda *_: 'PASS')
        self.source.rename(self.root / "unavailable-original")
        with patch('stm32_gdbtest.package.find_gdb', return_value='unused'):
            _, snapshot = open_configured(self.output, self.root/'receiver', 'unused')
        class Target:
            def check(self, name, actual, expected):
                if actual != expected:
                    raise AssertionError(name)
        t = ConfiguredTarget(Target(), snapshot)
        t.check('custom', t.config['api']['custom']['value'], 42)
        self.assertNotIn('records', t.config_props['api']['data'])
        with self.assertRaises(AttributeError):
            t.config = {}
        with self.assertRaises(TypeError):
            t.config_props['api']['data']['custom']['value'] = 3

    def test_stale_manifest_rejected_before_preflight(self):
        (self.source/'profile/target.toml').write_bytes(TARGET.replace('name="example"', 'name="changed"').encode())
        with self.assertRaisesRegex(ValueError, 'does not match target profile'):
            prepare_and_pack(self.session, self.output, ['HW_CONFIG'],
                             preflight=lambda *_: self.fail('preflight reached'))
        self.assertFalse(self.output.exists())

    def test_preflight_failure_never_creates_package(self):
        with self.assertRaisesRegex(RuntimeError, 'Preparation failed'):
            prepare_and_pack(self.session, self.output, ['HW_CONFIG'], preflight=lambda *_:'ERROR')
        self.assertFalse(self.output.exists())

    def test_packaged_config_cannot_disagree_with_profile(self):
        prepare_and_pack(self.session, self.output, ['HW_CONFIG'], preflight=lambda *_:'PASS')
        with zipfile.ZipFile(self.output) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        entries['profile/target.toml'] += b'\n# changed\n'
        manifest = json.loads(entries[MANIFEST])
        manifest['files']['profile/target.toml'] = hashlib.sha256(entries['profile/target.toml']).hexdigest()
        entries[MANIFEST] = json.dumps(manifest).encode()
        with zipfile.ZipFile(self.output, 'w') as archive:
            for name, raw in entries.items(): archive.writestr(name, raw)
        with patch('stm32_gdbtest.package.find_gdb', return_value='unused'):
            with self.assertRaisesRegex(ValueError, 'capsule target differs'):
                open_configured(self.output, self.root/'receiver', 'unused')


if __name__ == '__main__':
    unittest.main()
