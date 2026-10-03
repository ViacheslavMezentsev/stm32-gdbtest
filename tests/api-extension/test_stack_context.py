"""E3 host evidence for incompleteness, lifetime and consumer caller semantics."""

from dataclasses import FrozenInstanceError
import unittest
from stack_context import Contexts, GdbFrames, caller_is, interrupted_frame
from types import SimpleNamespace


class Backend:
    errors = (OSError,)
    def __init__(self):
        self.names = ['handler', None, 'board_delay_ms', 'app_loop']
        self.running = False
        self.broken = False
    def stopped(self): return not self.running
    def newest(self): return 0
    def register(self, frame, name): return 0x8000100 if name == 'pc' else 0x20001000
    def pc(self, frame): return 0x8000100 + frame * 4
    def name(self, frame): return self.names[frame]
    def kind(self, frame): return 'signal' if frame == 1 else 'normal'
    def older(self, frame):
        if self.broken: raise OSError('unwind failed')
        return frame + 1 if frame + 1 < len(self.names) else None


class ContextTests(unittest.TestCase):
    def test_gdb_without_first_error_constant(self):
        backend = GdbFrames.__new__(GdbFrames)
        backend.gdb = SimpleNamespace(FRAME_UNWIND_OUTERMOST=2, error=OSError,
                                      frame_stop_reason_string=lambda reason: str(reason))
        for reason in (0, 1, 3, 4, 5, 6, 7):
            frame = SimpleNamespace(older=lambda: None, unwind_stop_reason=lambda: reason)
            with self.assertRaises(OSError): backend.older(frame)
        frame = SimpleNamespace(older=lambda: None, unwind_stop_reason=lambda: 2)
        self.assertIsNone(backend.older(frame))

    def test_registers_frames_and_immutability(self):
        c = Contexts(Backend()).capture()
        self.assertEqual(c['PC'], 0x8000100)
        self.assertEqual(c['SP'], 0x20001000)
        self.assertTrue(c.stack.complete)
        self.assertEqual(interrupted_frame(c.stack).function, 'board_delay_ms')
        with self.assertRaises(KeyError): c['absent']
        with self.assertRaises(FrozenInstanceError): c.stack.frames[0].pc = 0

    def test_exact_depth_and_unknown_names(self):
        s = Contexts(Backend()).capture().stack
        self.assertIsNone(caller_is(s, 'board_delay_ms'))
        self.assertTrue(caller_is(s, 'board_delay_ms', depth=2))
        self.assertFalse(caller_is(s, 'handler', depth=2))
        self.assertFalse(caller_is(s, 'absent', depth=8))

    def test_truncation_is_not_absence(self):
        s = Contexts(Backend()).capture(max_frames=1).stack
        self.assertEqual(s.termination, 'depth_limit')
        self.assertFalse(s.complete)
        self.assertIsNone(caller_is(s, 'absent'))
        with self.assertRaises(RuntimeError): interrupted_frame(s)

    def test_unwind_error_retains_partial_stack(self):
        b = Backend(); b.broken = True
        s = Contexts(b).capture().stack
        self.assertEqual(s.termination, 'unwind_error')
        self.assertEqual(len(s.frames), 1)
        self.assertIsNone(caller_is(s, 'absent'))

    def test_invalidation_and_history(self):
        b = Backend(); owner = Contexts(b); old = owner.capture()
        self.assertTrue(owner.current(old))
        owner.invalidate()  # explicit mutation without resume
        self.assertFalse(owner.current(old))
        new = owner.capture()
        owner.invalidate(stopped=True)
        self.assertFalse(owner.current(new))
        self.assertEqual(old['PC'], 0x8000100)
        self.assertFalse(Contexts(b).current(owner.capture()))
        owner.close()
        self.assertFalse(owner.current(old))
        with self.assertRaises(RuntimeError): owner.capture()

    def test_running_and_invalid_limits(self):
        b = Backend(); c = Contexts(b); old = c.capture(); b.running = True
        self.assertFalse(c.current(old))
        with self.assertRaises(RuntimeError): c.capture()
        for limit in (0, True, 65, -1):
            with self.assertRaises(ValueError): c.capture(max_frames=limit)
