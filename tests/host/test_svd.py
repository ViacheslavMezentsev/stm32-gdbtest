"""TC-178: bounded SVD and source snapshots, no debugger access."""
import base64
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stm32_gdbtest import svd
from stm32_gdbtest.configuration import capture
from stm32_gdbtest.config_transport import dumps, loads
from stm32_gdbtest.package import pack, open_package
from stm32_gdbtest.runner import run
from test_session_config import TARGET

def xml(body=None):
    body = body or '<register><name>R</name><addressOffset>0</addressOffset></register>'
    return ('<device><name>D</name><addressUnitBits>8</addressUnitBits><size>32</size><access>read-write</access><peripherals><peripheral><name>P</name><baseAddress>0x40000000</baseAddress><registers>' + body + '</registers></peripheral></peripherals></device>').encode()

class SvdTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = xml()
        (self.root / 'target.toml').write_text(TARGET, encoding='utf-8')
        (self.root / 'session.toml').write_text('[config]\ntarget="target.toml"\n[mmio]\nsvd="device.svd"', encoding='utf-8')
        (self.root / 'device.svd').write_bytes(self.raw)
        board = self.root / 'tests' / 'board'
        board.mkdir(parents=True)
        (board / 'test_sample.py').write_text('@case("HW_SAMPLE")\ndef sample(t): pass\n', encoding='utf-8')
        (self.root / 'firmware.elf').write_bytes(b'fixture')
        self.session = dict(root=str(self.root), profile=str(self.root / 'target.toml'), session_config=str(self.root / 'session.toml'), tests=str(board), elf=str(self.root / 'firmware.elf'), gdb='unused', out=str(self.root / 'runs'))

    def test_immutable(self):
        c = svd.parse(self.raw)
        self.assertEqual(c.registers['P.R'].address, 1073741824)
        with self.assertRaises(TypeError):
            c.registers['P.R'] = None
        with self.assertRaises(FrozenInstanceError):
            c.registers['P.R'].address = 0

    def test_budgets(self):
        for key, value in [('bytes', len(self.raw) - 1), ('nodes', 2), ('depth', 2), ('copies', 1)]:
            with self.subTest(key=key), self.assertRaises(svd.SvdError) as cm:
                svd.parse(self.raw, replace(svd.Limits(), **{key: value}))
            self.assertEqual(cm.exception.code, 'svd.limit')
        svd.parse(self.raw, replace(svd.Limits(), bytes=len(self.raw)))

    def test_syntax_and_forbidden(self):
        for raw, code in [(b'\xff', 'svd.syntax'), (b'<device>', 'svd.syntax'), (b'<!DOCTYPE device>' + self.raw, 'svd.forbidden_construct'), (xml().replace(b'<size>', b'<TYPO>'), 'svd.syntax')]:
            with self.subTest(code=code), self.assertRaises(svd.SvdError) as cm:
                svd.parse(raw)
            self.assertEqual(cm.exception.code, code)

    def test_array_and_cluster(self):
        raw = xml('<cluster><name>C%s</name><dim>2</dim><dimIncrement>16</dimIncrement><addressOffset>0</addressOffset><size>16</size><access>read-only</access><register><name>R</name><addressOffset>2</addressOffset></register></cluster>')
        c = svd.parse(raw)
        self.assertEqual(c.registers['P.C1.R'].address, 1073741842)
        self.assertEqual(c.registers['P.C1.R'].access, 'read-only')
        for key, value in [('registers', 1), ('instances', 2)]:
            with self.assertRaises(svd.SvdError) as cm:
                svd.parse(raw, replace(svd.Limits(), **{key: value}))
            self.assertEqual(cm.exception.code, 'svd.limit')

    def test_derived_and_effects(self):
        raw = xml('<register><name>R</name><addressOffset>0</addressOffset><readAction>clear</readAction><modifiedWriteValues>oneToClear</modifiedWriteValues></register><register derivedFrom="P.R"><name>S</name><addressOffset>4</addressOffset></register>')
        r = svd.parse(raw).registers['P.S']
        self.assertEqual((r.read_action, r.write_effect), ('clear', 'oneToClear'))
        for raw in [raw.replace(b'P.R', b'P.MISSING'), xml('<register derivedFrom="R"><name>R</name></register>')]:
            with self.assertRaises(svd.SvdError) as cm:
                svd.parse(raw)
            self.assertEqual(cm.exception.code, 'svd.reference')

    def test_unknown_access_not_defaulted(self):
        with self.assertRaises(svd.SvdError):
            svd.parse(self.raw.replace(b'read-write', b'rw'))
        r = svd.parse(self.raw.replace(b'<access>read-write</access>', b'')).registers['P.R']
        self.assertIsNone(r.access)

    def test_source_error_before_execute(self):
        (self.root / 'device.svd').unlink()
        with self.assertRaises(svd.SvdError) as cm:
            capture(self.session, environ={})
        self.assertEqual(cm.exception.code, 'svd.source')
        with patch.dict(os.environ, {}, clear=True), patch('stm32_gdbtest.runner.execute') as execute:
            self.assertEqual(run(self.session, dict(id='HW_SAMPLE', timeout_s=5), prepare_only=True), 2)
            execute.assert_not_called()

    def test_capsule_freezes_source(self):
        c = capture(self.session, environ={})
        encoded = dumps(c)
        (self.root / 'device.svd').unlink()
        restored = loads(encoded)
        self.assertEqual(restored._source_bytes['svd'], self.raw)
        self.assertEqual(restored.svd_catalog.sha256, hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(json.loads(encoded)['schema'], 2)

    def test_corrupt_capsule(self):
        data = json.loads(dumps(capture(self.session, environ={})))
        data['files']['svd']['base64'] = base64.b64encode(b'changed').decode()
        with self.assertRaises(svd.SvdError) as cm:
            loads(json.dumps(data))
        self.assertEqual(cm.exception.code, 'svd.integrity')

    def test_no_svd_compatible(self):
        (self.root / 'session.toml').write_text('[config]\ntarget="target.toml"', encoding='utf-8')
        c = capture(self.session, environ={})
        self.assertIsNone(c.svd_catalog)
        self.assertEqual(json.loads(dumps(c))['schema'], 1)
        self.assertIsNone(loads(dumps(c)).svd_catalog)

    def test_package_without_original(self):
        self.session['_config_capsule'] = dumps(capture(self.session, environ={}))
        (self.root / 'device.svd').write_bytes(b'changed')
        archive = self.root / 'bundle.zip'
        pack(self.session, archive)
        (self.root / 'device.svd').unlink()
        (self.root / 'session.toml').unlink()
        with patch('stm32_gdbtest.package.find_gdb', return_value='unused'):
            received = open_package(archive, self.root / 'receiver')
        self.assertEqual(capture(received, environ={})._source_bytes['svd'], self.raw)
    def test_save_failure_and_integrity(self):
        c = svd.parse(self.raw)
        self.assertEqual(svd.save_source(self.root, c, self.raw)['sha256'], c.sha256)
        for method, value, code in [('write_bytes', OSError('disk'), 'svd.capture'),
                                     ('read_bytes', b'wrong', 'svd.integrity')]:
            kwargs = {'side_effect': value} if isinstance(value, Exception) else {'return_value': value}
            with patch.object(Path, method, **kwargs), self.assertRaises(svd.SvdError) as cm:
                svd.save_source(self.root, c, self.raw)
            self.assertEqual(cm.exception.code, code)
        with self.assertRaises(svd.SvdError): svd.save_source(self.root, c, b'wrong')

    def test_field_policy_and_constraints(self):
        raw = xml('<register><name>R</name><addressOffset>0</addressOffset><fields>'
                  '<field><name>F</name><bitOffset>0</bitOffset><bitWidth>1</bitWidth>'
                  '<access>read-only</access><readAction>clear</readAction></field>'
                  '</fields><writeConstraint><writeAsRead>true</writeAsRead></writeConstraint></register>')
        r = svd.parse(raw).registers['P.R']
        self.assertEqual(r.fields[0][3:5], ('read-only', 'clear'))
        self.assertTrue(r.constraint)

    def test_derived_depth_limit(self):
        body = '<register><name>R0</name><addressOffset>0</addressOffset></register>'
        for i in range(1, 35):
            body += f'<register derivedFrom="R{i-1}"><name>R{i}</name><addressOffset>{i*4}</addressOffset></register>'
        with self.assertRaises(svd.SvdError) as cm: svd.parse(xml(body))
        self.assertEqual(cm.exception.code, 'svd.limit')

    def test_capsule_size_and_reference(self):
        data = json.loads(dumps(capture(self.session, environ={})))
        data['files']['svd']['base64'] = 'A' * (4*((svd.Limits().bytes+2)//3)+1)
        with self.assertRaises(svd.SvdError) as cm: loads(json.dumps(data))
        self.assertEqual(cm.exception.code, 'svd.limit')

    def test_runner_saves_snapshot_before_tools(self):
        # A later ELF failure must leave the selected SVD evidence, without tools.
        (self.root/'firmware.elf').unlink()
        with patch.dict(os.environ, {}, clear=True), patch('stm32_gdbtest.runner.runtime_manifest', return_value={}), patch('stm32_gdbtest.runner.subprocess.run') as tools:
            self.assertEqual(run(self.session, dict(id='HW_SAMPLE', timeout_s=5), prepare_only=True), 2)
            tools.assert_not_called()
        output = next((self.root/'runs').iterdir())
        self.assertEqual((output/'source.svd').read_bytes(), self.raw)
        self.assertEqual(loads((output/'config.json').read_text())._source_bytes['svd'], self.raw)

if __name__ == '__main__':
    unittest.main()
