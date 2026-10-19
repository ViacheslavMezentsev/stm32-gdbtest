"""ТЗ 5.27: offline HIL inspection, including failures and zero execution."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stm32_gdbtest.configuration import load_session
from stm32_gdbtest.config_transport import dumps
from stm32_gdbtest import hil_inspect
from stm32_gdbtest.hil_inspect import inspect


def main(argv):
    parser = argparse.ArgumentParser()
    hil_inspect.configure_parser(parser)
    return hil_inspect.main(parser.parse_args(argv))


class Tests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hil space-')
        self.root = Path(self.tmp.name)
        self.stack = contextlib.ExitStack()
        self.stack.enter_context(patch.dict(os.environ, {}, clear=False))
        os.environ.pop('STM32_GDBTEST_STAND', None)
        for name in ('Popen', 'run', 'check_output', 'check_call'):
            self.stack.enter_context(patch.object(subprocess, name, side_effect=AssertionError('external process forbidden')))
        self.stack.enter_context(patch.object(socket, 'socket', side_effect=AssertionError('socket forbidden')))

    def tearDown(self):
        self.stack.close()
        self.tmp.cleanup()

    def write(self, p, s):
        p = self.root / p
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(s, encoding='utf-8')
        return p

    def fixture(self, compact=True, prefix=''):
        base = Path(prefix) / 'hil'
        entry = base / ('F103/session.toml' if compact else 'sessions/f103.toml')
        target = base / ('F103/target.toml' if compact else 'profiles/f103.toml')
        self.write(target, (ROOT / 'tests/renode-backend/target.toml').read_text())
        self.write(entry, '[config]\ntarget = "' + ('target.toml' if compact else '../profiles/f103.toml') + '"\n')
        profile = base / 'common' if compact else base
        self.write(profile / 'tests/requirements.md', '## HW_BOOT\n')
        self.write(profile / 'tests/board/test_boot.py', 'raise RuntimeError("MUST NOT IMPORT")\n@case("HW_BOOT", labels=("boot",))\ndef test(t): pass\n')
        return (self.root / entry, self.root / profile)

    def check(self, pair, **kw):
        return inspect(config=pair[0], profile_dir=pair[1], project_root=self.root, **kw)

    def test_layouts(self):
        a = self.check(self.fixture(True, 'a'))
        b = self.check(self.fixture(False, 'b'))
        self.assertTrue(a['configuration_valid'])
        self.assertTrue(b['configuration_valid'])
        self.assertEqual([x['id'] for x in a['scenarios']], [x['id'] for x in b['scenarios']])

    def test_missing(self):
        pair = self.fixture()
        (pair[0].parent / 'target.toml').unlink()
        self.assertFalse(self.check(pair)['configuration_valid'])

    def test_schema(self):
        pair = self.fixture()
        pair[0].write_text('[unknown]\nx=1')
        self.assertFalse(self.check(pair)['configuration_valid'])

    def test_duplicate(self):
        pair = self.fixture()
        self.write('hil/common/tests/board/test_other.py', '@case("HW_BOOT")\ndef other(t): pass\n')
        self.assertFalse(self.check(pair)['configuration_valid'])

    def test_requirements(self):
        pair = self.fixture()
        self.write('hil/common/tests/requirements.md', '## HW_OTHER\n')
        self.assertFalse(self.check(pair)['configuration_valid'])

    def test_nonrecursive(self):
        pair = self.fixture()
        self.write('hil/common/tests/board/nested/test_bad.py', 'invalid!!!')
        self.assertTrue(self.check(pair)['configuration_valid'])

    def test_cwd_absolute(self):
        pair = self.fixture(prefix='кириллица')
        before = self.check(pair)
        old = Path.cwd()
        try:
            os.chdir(self.root)
            after = self.check(pair)
        finally:
            os.chdir(old)
        self.assertEqual(before, after)

    def test_runtime_cwd(self):
        pair = self.fixture()
        runtime = self.write('run.json', json.dumps(dict(session_config='hil/F103/session.toml', profile='hil/F103/target.toml', tests='hil/common/tests/board')))
        old = Path.cwd()
        try:
            os.chdir(self.root)
            self.assertTrue(inspect(session=runtime, project_root=self.root)['configuration_valid'])
            os.chdir(self.root.parent)
            self.assertFalse(inspect(session=runtime, project_root=self.root)['configuration_valid'])
        finally:
            os.chdir(old)

    def test_stale(self):
        pair = self.fixture()
        p = self.write('run.json', json.dumps(dict(session_config=str(pair[0]), profile=str(self.root / 'wrong'), tests=str(pair[1] / 'tests/board'))))
        self.assertFalse(inspect(session=p, project_root=self.root)['configuration_valid'])

    def test_external_redacted(self):
        pair = self.fixture()
        r = inspect(config=pair[0], profile_dir=pair[1], project_root=self.root / 'unrelated')
        self.assertTrue(r['configuration_valid'])
        self.assertNotIn(str(self.root), json.dumps(r))

    def test_qemu_no_execute(self):
        pair = self.fixture()
        stand = self.write('stand.toml', 'schema=1\n[emulator]\nbackend="qemu"\nexecutable="python"\n[qemu]\nmachine="netduinoplus2"\n')
        stand.write_text(stand.read_text().replace(chr(34) + 'python' + chr(34), json.dumps(sys.executable)), encoding='utf-8')
        r = self.check(pair, stand=stand)
        self.assertTrue(r['configuration_valid'])
        self.assertEqual(r['backend'], 'qemu')

    def test_renode_relative(self):
        pair = self.fixture()
        self.write('models/p.repl', 'cpu: CPU.CortexM @ sysbus\n')
        stand = self.write('models/s.toml', 'schema=1\n[emulator]\nbackend="renode"\nexecutable="python"\n[renode]\nplatform="p.repl"\n')
        stand.write_text(stand.read_text().replace(chr(34) + 'python' + chr(34), json.dumps(sys.executable)), encoding='utf-8')
        r = self.check(pair, stand=stand)
        self.assertTrue(r['configuration_valid'])
        self.assertTrue(any((n['id'] == 'platform' for n in r['nodes'])))

    def test_svd_missing(self):
        pair = self.fixture()
        pair[0].write_text(pair[0].read_text() + '\n[mmio]\nsvd="model.svd"\n')
        self.assertFalse(self.check(pair)['configuration_valid'])

    def test_fifty(self):
        for i in range(50):
            self.assertTrue(self.check(self.fixture(i % 2 == 0, str(i)))['configuration_valid'])

class Current(Tests):

    def svd_fixture(self):
        pair = self.fixture()
        self.write('hil/F103/model.svd', (ROOT / 'tests/mmio-renode/teaching-expanded.svd').read_text())
        pair[0].write_text(pair[0].read_text() + '\n[mmio]\nsvd="model.svd"\n')
        return pair

    def test_svd_valid(self):
        r = self.check(self.svd_fixture())
        self.assertTrue(r['configuration_valid'], r)
        self.assertEqual(r['svd']['semantics'], 'VALID')
        self.assertGreater(r['svd']['registers'], 7)
        self.assertEqual(len(next((n for n in r['nodes'] if n['id'] == 'svd'))['sha256']), 64)

    def test_svd_semantics_invalid(self):
        pair = self.svd_fixture()
        self.write('hil/F103/model.svd', '<device/>')
        r = self.check(pair)
        self.assertEqual(r['svd']['availability'], 'FOUND')
        self.assertEqual(r['svd']['semantics'], 'INVALID')
        self.assertIn('svd.invalid', [d['code'] for d in r['diagnostics']])

    def test_svd_dtd(self):
        pair = self.svd_fixture()
        self.write('hil/F103/model.svd', '<!DOCTYPE x [<!ENTITY x SYSTEM "file:///secret">]><device/>')
        self.assertFalse(self.check(pair)['configuration_valid'])

    def test_svd_budget(self):
        from stm32_gdbtest.svd import Limits
        pair = self.svd_fixture()
        with patch('stm32_gdbtest.svd.Limits', return_value=Limits(bytes=10)):
            self.assertFalse(self.check(pair)['configuration_valid'])

    def runtime(self, pair, capsule=None):
        data = dict(session_config=str(pair[0]), profile=str(pair[0].parent / 'target.toml'), tests=str(pair[1] / 'tests/board'))
        if capsule is not None:
            data['_config_capsule'] = capsule
        return self.write('runtime.json', json.dumps(data))

    def test_capsule_no_reopen(self):
        pair = self.svd_fixture()
        cap = dumps(load_session(pair[0]))
        runtime = self.runtime(pair, cap)
        for name in ('session.toml', 'target.toml', 'model.svd'):
            (pair[0].parent / name).unlink()
        r = inspect(session=runtime, project_root=self.root)
        self.assertTrue(r['configuration_valid'], r)
        self.assertEqual(r['svd']['source'], 'capsule')
        self.assertEqual(r['selection']['source'], 'capsule')

    def test_capsule_integrity(self):
        pair = self.svd_fixture()
        cap = json.loads(dumps(load_session(pair[0])))
        cap['files']['svd']['sha256'] = '0' * 64
        r = inspect(session=self.runtime(pair, json.dumps(cap)), project_root=self.root)
        self.assertIn('svd.integrity', [d['code'] for d in r['diagnostics']])

    def test_input_conflict(self):
        pair = self.fixture()
        r = inspect(config=pair[0], session='x')
        self.assertEqual(r['diagnostics'][0]['code'], 'input.conflict')

    def test_duplicate_roots(self):
        pair = self.fixture()
        self.assertFalse(self.check(pair, test_dirs=[pair[1] / 'tests'])['configuration_valid'])

    def test_schema_and_determinism(self):
        pair = self.svd_fixture()
        a = self.check(pair)
        b = self.check(pair)
        self.assertEqual(a, b)
        self.assertEqual(set(a), {'schema', 'scope', 'runtime_checked', 'selection', 'nodes', 'edges', 'scenarios', 'diagnostics', 'svd', 'summary', 'configuration_valid'})
        for d in a['diagnostics']:
            self.assertEqual(set(d), {'code', 'severity', 'node', 'field', 'message'})
        self.assertFalse(a['runtime_checked'])

    def test_backend_matrix(self):
        import sys
        for backend in ('openocd', 'jlink', 'st-util', 'stlink'):
            with self.subTest(backend=backend):
                pair = self.fixture(prefix=backend)
                (pair[0].parent / 'target.toml').write_text((ROOT / 'tests/firmware/profiles/f411ce/target.toml').read_text())
                text = '[probe]\nbackend=' + json.dumps(backend) + '\nserial="123456789012345678901234"\nexecutable=' + json.dumps(sys.executable) + '\n'
                if backend == 'stlink':
                    self.write('programmer/' + __import__('stm32_gdbtest.backends', fromlist=['PROGRAMMER']).PROGRAMMER, 'dummy')
                    text += 'programmer_dir=' + json.dumps(str(self.root / 'programmer')) + '\n'
                r = self.check(pair, stand=self.write(backend + '.toml', text))
                self.assertTrue(r['configuration_valid'], r)
                self.assertIsNone(next((n for n in r['nodes'] if n['id'] == 'executable'))['sha256'])
                self.assertNotIn('123456789012345678901234', json.dumps(r))

    def test_remote_deferred_and_privacy(self):
        import sys
        pair = self.fixture()
        (pair[0].parent / 'target.toml').write_text((ROOT / 'tests/firmware/profiles/f411ce/target.toml').read_text())
        key = self.write('secret-key', 'SECRET-KEY-CONTENTS')
        stand = self.write('remote.toml', '[probe]\nbackend="openocd"\nserial="PRIVATE123"\nexecutable="/remote/missing/openocd"\n[remote]\nhost="private-host"\nssh=' + json.dumps(sys.executable) + '\nidentity_file=' + json.dumps(str(key)) + '\n')
        r = self.check(pair, stand=stand)
        self.assertTrue(r['configuration_valid'], r)
        self.assertEqual(r['summary']['DEFERRED'], 2)
        for secret in ('private-host', 'PRIVATE123', 'secret-key', 'SECRET-KEY-CONTENTS', '/remote/missing'):
            self.assertNotIn(secret, json.dumps(r))

    def test_backend_mismatch(self):
        import sys
        pair = self.fixture()
        (pair[0].parent / 'target.toml').write_text((ROOT / 'tests/firmware/profiles/f411ce/target.toml').read_text())
        stand = self.write('q.toml', 'schema=1\n[emulator]\nbackend="qemu"\nexecutable=' + json.dumps(sys.executable) + '\n[qemu]\nmachine="netduinoplus2"\n')
        r = self.check(pair, stand=stand)
        self.assertIn('backend.environment_mismatch', [d['code'] for d in r['diagnostics']])

    def test_cli_codes_and_output(self):
        pair = self.fixture()
        args = ['--config', str(pair[0]), '--profile-dir', str(pair[1]), '--format', 'json']
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(args), 0)
            self.assertEqual(json.loads(out.getvalue())['summary']['WARN'], 1)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(args + ['--warnings-as-errors']), 2)
        dest = self.root / 'report.json'
        self.assertEqual(main(args + ['--output', str(dest)]), 0)
        self.assertTrue(json.loads(dest.read_text())['configuration_valid'])
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args + ['--output', str(self.root / 'missing' / 'report')]), 2)

    def test_no_leak_in_error(self):
        pair = self.svd_fixture()
        self.write('hil/F103/model.svd', '<device><name>PRIVATE-PATH</name><size>PRIVATE-SECRET</size></device>')
        r = self.check(pair)
        self.assertNotIn('PRIVATE', json.dumps(r))

    def test_async_discovery(self):
        pair = self.fixture()
        self.write('hil/common/tests/board/test_boot.py', '@case("HW_BOOT")\nasync def test(t): await t.wait()\n')
        self.assertTrue(self.check(pair)['configuration_valid'])

    def test_directory_alias(self):
        pair = self.fixture()
        link = self.root / 'alias'
        if os.name == 'nt':
            import _winapi
            _winapi.CreateJunction(str(pair[1]), str(link))
        else:
            link.symlink_to(pair[1], target_is_directory=True)
        r = inspect(config=pair[0], profile_dir=link, project_root=self.root)
        self.assertTrue(r['configuration_valid'], r)
        self.assertTrue(any((n['path'] != n['resolved_path'] for n in r['nodes'])))

    def test_missing_executable(self):
        pair = self.fixture()
        stand = self.write('q.toml', 'schema=1\n[emulator]\nbackend="qemu"\nexecutable="nonexistent-tool-836172"\n[qemu]\nmachine="netduinoplus2"\n')
        r = self.check(pair, stand=stand)
        self.assertIn('backend.invalid', [d['code'] for d in r['diagnostics']])

    def test_renode_include_rejected(self):
        import sys
        pair = self.fixture()
        self.write('p.repl', 'using "external.repl"\n')
        stand = self.write('r.toml', 'schema=1\n[emulator]\nbackend="renode"\nexecutable=' + json.dumps(sys.executable) + '\n[renode]\nplatform="p.repl"\n')
        self.assertFalse(self.check(pair, stand=stand)['configuration_valid'])

    def test_public_cli(self):
        from stm32_gdbtest.cli import main as cli
        pair = self.fixture()
        with patch.object(sys, 'argv', ['stm32-gdbtest', 'inspect', '--config', str(pair[0]), '--profile-dir', str(pair[1]), '--format', 'json']), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cli(), 0)
            self.assertEqual(json.loads(out.getvalue())['schema'], 1)

    def test_malformed_runtime(self):
        for raw in ('[]', 'null', '{"tests": 1}'):
            with self.subTest(raw=raw):
                r = inspect(session=self.write('bad.json', raw))
                self.assertFalse(r['configuration_valid'])
    def test_parent_reference_redacted(self):
        pair = self.fixture()
        outside = self.write('private-parent/target.toml', (pair[0].parent / 'target.toml').read_text())
        pair[0].write_text('[config]\ntarget="../../private-parent/target.toml"\n')
        result = inspect(config=pair[0], profile_dir=pair[1], project_root=self.root / 'hil')
        self.assertTrue(result['configuration_valid'], result)
        self.assertNotIn('private-parent', json.dumps(result))

if __name__ == '__main__':
    unittest.main(verbosity=2)
