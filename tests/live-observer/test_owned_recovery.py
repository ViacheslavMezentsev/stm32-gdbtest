import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from fpb_adapter import Adapter, CTRL, REMAP, COMP
from recovery_fpb import clear_owned

class Memory:

    def __init__(self):
        self.mem = {}
        self.writes = 0
        self.store(CTRL, struct.pack('<10I', 609, 0x20000000, 0, 0, 0, 0, 0, 0, 0, 0))
        self.store(0x20008300, b'\xa5' * 32)

    def store(self, a, data):
        for i, x in enumerate(data):
            self.mem[a + i] = x

    def read(self, a, n):
        return bytes((self.mem[a + i] for i in range(n)))

    def halted(self):
        return True

    def write(self, a, data):
        self.writes += 1
        if a == CTRL:
            data = struct.pack('<I', 608 | int.from_bytes(data, 'little') & 1)
        if a == REMAP:
            data = struct.pack('<I', 0x20000000 | int.from_bytes(data, 'little') & 0x1fffffe0)
        self.store(a, data)

class Tests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.io = Memory()
        self.before = dict(self.io.mem)
        events = []
        Adapter(self.io, events.append).install((0x20008000, 1024), 0x20008300, 0x20008034, target=0x800021c)
        p = self.d / 'events.jsonl'
        p.write_text('\n'.join(map(json.dumps, events)))
        self.config = dict(p4_package=str(self.d), p4_events=str(p))
        self.m = dict(remap_table=0x20008300, function=0x800021c, fpb_hook=0x20008034)
        self.io.writes = 0

    def tearDown(self):
        self.tmp.cleanup()

    def run_recovery(self):
        with patch('sealed.validate', return_value=self.m):
            return clear_owned(self.io, self.config)

    def test_owned(self):
        self.assertEqual(self.run_recovery(), 'VERIFIED')
        self.assertEqual(self.io.mem, self.before)

    def test_foreign_comparator(self):
        self.io.store(COMP, struct.pack('<I', 0x8000901))
        with self.assertRaises(RuntimeError):
            self.run_recovery()
        self.assertEqual(self.io.writes, 0)

    def test_wrong_target(self):
        self.m['function'] += 4
        with self.assertRaises(RuntimeError):
            self.run_recovery()
        self.assertEqual(self.io.writes, 0)

    def test_incomplete_table(self):
        self.io.mem[0x20008300] = 1
        with self.assertRaises(RuntimeError):
            self.run_recovery()
        self.assertEqual(self.io.writes, 0)

    def test_missing_evidence(self):
        Path(self.config['p4_events']).unlink()
        with self.assertRaises(FileNotFoundError):
            self.run_recovery()
        self.assertEqual(self.io.writes, 0)

    def test_corrupt_package(self):
        with patch('sealed.validate', side_effect=ValueError('hash')):
            with self.assertRaises(ValueError):
                clear_owned(self.io, self.config)
        self.assertEqual(self.io.writes, 0)

    def test_partial_install(self):
        self.io.store(COMP + 28, bytes(4))
        self.assertEqual(self.run_recovery(), 'VERIFIED')

    def test_no_fpb(self):
        self.io.mem = dict(self.before)
        self.assertEqual(self.run_recovery(), 'NOT_NEEDED')
        self.assertEqual(self.io.writes, 0)
if __name__ == '__main__':
    unittest.main()
