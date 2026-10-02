from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lab.navigation import self_branch, caller_is
from lab.openocd_native import native_swd


class RecognitionTests(unittest.TestCase):
    def test_native_transport_keeps_debugger_and_target_selection(self):
        command = ['openocd', '-f', 'interface/stlink.cfg', '-f', 'target/stm32f4x.cfg',
                   '-c', 'adapter serial EXAMPLE', '-c', 'adapter speed 1000']
        result = native_swd(command)
        self.assertEqual(result[1:5], ['-f', 'interface/stlink-dap.cfg', '-c', 'transport select dapdirect_swd'])
        self.assertEqual(result[5:], command[3:])
        self.assertEqual(command[2], 'interface/stlink.cfg')
        with self.assertRaises(ValueError):
            native_swd(['openocd', '-f', 'other.cfg'])

    def test_address_format_does_not_affect_recognition(self):
        self.assertTrue(self_branch(0x800000a, 'b.n 0X0800000A <Default_Handler>'))
        self.assertTrue(self_branch(0x800000a, 'b.w 0x800000a'))

    def test_conditional_or_other_target_is_not_a_proven_loop(self):
        for asm in ('bne.n 0x800000a', 'b.n 0x800000c', 'bl 0x800000a', 'b.n symbol', ''):
            self.assertFalse(self_branch(0x800000a, asm))

    def test_callers_are_depth_sensitive_and_bounded_by_stack(self):
        main = SimpleNamespace(name=lambda: 'main', older=lambda: None)
        parent = SimpleNamespace(name=lambda: 'parent', older=lambda: main)
        child = SimpleNamespace(name=lambda: 'child', older=lambda: parent)
        self.assertTrue(caller_is(child, 'parent'))
        self.assertTrue(caller_is(child, 'main', 2))
        self.assertFalse(caller_is(child, 'main'))
        self.assertFalse(caller_is(child, 'main', 20))

    def test_invalid_depth_is_not_current_frame(self):
        for depth in (0, -1, True, '1'):
            with self.assertRaises(ValueError):
                caller_is(None, 'main', depth)
