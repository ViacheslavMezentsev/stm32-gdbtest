"""Explicit host checks of the teaching model, without importing Renode."""
from pathlib import Path
from types import SimpleNamespace
import unittest


class TeachingModelTest(unittest.TestCase):
    def setUp(self):
        self.memory = {}
        bus = SimpleNamespace(WriteByte=lambda address, value: self.memory.__setitem__(address, value))
        machine = SimpleNamespace(SystemBus=bus)
        self.scope = {"self": SimpleNamespace(GetMachine=lambda: machine)}
        self.code = compile(Path(__file__).with_name("flash_model.py").read_text(), "flash_model.py", "exec")
        self.access("init")

    def access(self, kind, offset=0, value=0):
        request = SimpleNamespace(IsInit=kind == "init", IsRead=kind == "read", IsWrite=kind == "write",
                                  Offset=offset, Value=value)
        self.scope["request"] = request
        exec(self.code, self.scope)
        return request.Value

    def test_keys_and_fresh_instance(self):
        self.access("write", 8, 0x12345678)
        self.access("write", 8, 0xCDEF89AB)
        self.assertEqual(self.access("read", 0x14), 0x80000000)
        self.access("write", 8, 0x45670123)
        self.access("write", 8, 0xCDEF89AB)
        self.assertEqual(self.access("read", 0x14), 0)
        self.access("init")
        self.assertEqual(self.access("read", 0x14), 0x80000000)

    def test_boundary_erase_and_lock_gap(self):
        for page in (127, 128, 255):
            with self.subTest(page=page):
                self.access("init")
                start = 0x08000000 + page * 2048
                self.memory = {start - 1: 17, start + 2048: 34}
                control = ((page % 128) << 3) | (0x800 if page >= 128 else 0) | 2 | 0x10000
                self.access("write", 0x14, control)
                self.assertEqual(len(self.memory), 2050)
                self.assertTrue(all(self.memory[start + i] == 255 for i in range(2048)))
                self.assertEqual((self.memory[start - 1], self.memory[start + 2048]), (17, 34))
                self.assertFalse(self.access("read", 0x14) & 0x10000)
                self.assertEqual(self.access("read", 0x10), 1)

    def test_completion_without_programming(self):
        self.memory[0x08000000] = 0xA5
        self.access("write", 0x14, 1)
        self.assertEqual(self.memory, {0x08000000: 0xA5})
        self.assertEqual(self.access("read", 0x10), 1)

    def test_flag_clear_both_offsets(self):
        for offset in (0x10, 0x18):
            self.access("write", 0x14, 1)
            self.access("write", offset, 1)
            self.assertEqual(self.access("read", 0x10), 0)


if __name__ == "__main__":
    unittest.main()
