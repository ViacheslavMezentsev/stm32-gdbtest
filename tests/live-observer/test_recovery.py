import json, tempfile, unittest
from pathlib import Path
from recovery import backup, restore, FLASH, RAM

class Fake:

    def __init__(self):
        self.f = bytearray(b'F' * 2048)
        self.r = bytearray(b'R' * 4096)
        self.calls = []
        self.bad = None

    def qualify(self, g, i):
        self.calls.append('qualify')

    def reset_halt(self):
        self.calls.append('reset')
        self.r[:] = b'0' * len(self.r)

    def halt(self):
        self.calls.append('halt')

    def halted(self):
        return self.bad != 'running'

    def state(self):
        return {'halted': True}

    def read(self, a, n):
        data = bytes(self.f if a == FLASH else self.r)[:n]
        return data[:-1] if self.bad == 'short' else data

    def write(self, a, data):
        self.calls.append('ram_write')
        if self.bad == 'write':
            raise TimeoutError('lost ACK')
        self.r[:] = data if self.bad != 'ram_mismatch' else b'X' * len(data)

    def make_restore(self, f, n, elf):
        Path(elf).write_bytes(Path(f).read_bytes()[:n])

    def program(self, p):
        self.calls.append('flash_write')
        if self.bad == 'flash':
            raise TimeoutError('flash error')
        self.f[:1024] = Path(p).read_bytes()
        self.r[:] = b'X' * len(self.r)

class Tests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name) / 'backup'
        self.io = Fake()
        backup(self.io, self.d, {'sector': 1024, 'flash_size': 2048, 'ram_size': 4096}, {})
        self.io.calls.clear()

    def tearDown(self):
        self.tmp.cleanup()

    def test_backup_does_not_reset(self):
        fresh = Fake()
        d = self.d.parent / 'no-reset'
        backup(fresh, d, {'sector': 1024, 'flash_size': 2048, 'ram_size': 4096}, {})
        self.assertNotIn('reset', fresh.calls)
        self.assertEqual((d / 'ram.bin').read_bytes(), b'R' * 4096)

    def test_unchanged_flash(self):
        r = restore(self.io, self.d)
        self.assertEqual(r['recovery'], 'VERIFIED')
        self.assertNotIn('flash_write', self.io.calls)

    def test_flash_then_ram(self):
        self.io.f[0] = 0
        restore(self.io, self.d)
        self.assertLess(self.io.calls.index('flash_write'), self.io.calls.index('ram_write'))
        self.assertEqual(bytes(self.io.r), (self.d / 'ram.bin').read_bytes())

    def test_corrupt_backup_before_connect(self):
        for name in ('flash.bin', 'ram.bin', 'restore.elf'):
            with self.subTest(name=name):
                p = self.d / name
                original = p.read_bytes()
                p.write_bytes(b'bad')
                with self.assertRaises(RuntimeError):
                    restore(self.io, self.d)
                self.assertEqual(self.io.calls, [])
                p.write_bytes(original)

    def test_outside_block(self):
        self.io.f[1500] = 0
        with self.assertRaises(RuntimeError):
            restore(self.io, self.d)
        self.assertNotIn('flash_write', self.io.calls)
        self.assertNotIn('ram_write', self.io.calls)

    def test_short_read(self):
        self.io.bad = 'short'
        with self.assertRaises(RuntimeError):
            restore(self.io, self.d)
        self.assertNotIn('ram_write', self.io.calls)

    def test_no_halt(self):
        self.io.bad = 'running'
        with self.assertRaises(RuntimeError):
            restore(self.io, self.d)
        self.assertNotIn('ram_write', self.io.calls)

    def test_flash_error_no_ram(self):
        self.io.f[0] = 0
        self.io.bad = 'flash'
        with self.assertRaises(TimeoutError):
            restore(self.io, self.d)
        self.assertNotIn('ram_write', self.io.calls)

    def test_ambiguous_write_no_retry(self):
        self.io.bad = 'write'
        with self.assertRaises(TimeoutError):
            restore(self.io, self.d)
        self.assertEqual(self.io.calls.count('ram_write'), 1)
        self.assertEqual(json.loads((self.d / 'recovery.json').read_text())['recovery'], 'ERROR')

    def test_ram_mismatch(self):
        self.io.bad = 'ram_mismatch'
        with self.assertRaises(RuntimeError):
            restore(self.io, self.d)

    def test_backup_short_no_verified(self):
        self.io.bad = 'short'
        p = self.d.parent / 'bad'
        with self.assertRaises(RuntimeError):
            backup(self.io, p, {'flash_size': 2048, 'ram_size': 4096, 'sector': 1024}, {})
        self.assertFalse((p / 'manifest.json').exists())
if __name__ == '__main__':
    unittest.main()
