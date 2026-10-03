"""E4 stop classification and cleanup failures, without claiming an ABI model."""

from types import SimpleNamespace
import unittest
from natural_finish import finish, FinishError


class Backend:
    errors = (OSError,)
    def __init__(self):
        self.kind = 'integer'
        self.stop = {'breakpoints':[9]}
        self.matches = True
        self.value = -7
        self.cleaned = False
        self.resumed = False
        self.fail_prepare = False
        self.fail_resume = False
        self.fail_cleanup = False
        self.fail_value = False
        self.cleanup_errors = []
    def prepare(self):
        if self.fail_prepare: raise FinishError('no headroom')
        return {'kind':self.kind, 'type_name':'int32_t'}
    def point(self, plan): return SimpleNamespace(number=9)
    def resume(self):
        self.resumed = True
        if self.fail_resume: raise TimeoutError('primary timeout')
        return self.stop
    def at_return(self, plan): return self.matches
    def return_value(self, plan):
        if self.fail_value: raise OSError('register unavailable')
        return self.value
    def cleanup(self, point):
        self.cleaned = True
        if self.fail_cleanup: raise OSError('cleanup failure')


class FinishTests(unittest.TestCase):
    def test_temporary_point_expires_on_resume(self):
        b = Backend()
        class Temporary:
            @property
            def number(self):
                if b.resumed: raise RuntimeError('invalid breakpoint')
                return 9
        b.point = lambda plan: Temporary()
        self.assertEqual(finish(b).outcome, 'returned')

    def test_natural_integer_and_void(self):
        b = Backend(); r = finish(b)
        self.assertEqual((r.outcome,r.value_state,r.value), ('returned','available',-7))
        self.assertTrue(b.cleaned)
        b.kind = 'void'; r = finish(b)
        self.assertEqual((r.value_state,r.value), ('void',None))

    def test_interruption_and_coincident_points(self):
        for stop in ({'breakpoints':[3]}, {'breakpoints':[9,3]}, {'signal':'SIGINT'}, {}):
            b = Backend(); b.stop = stop
            r = finish(b)
            self.assertEqual(r.outcome, 'interrupted')
            self.assertEqual(r.value_state, 'not_returned')
            self.assertTrue(b.cleaned)

    def test_wrong_return_stack(self):
        b = Backend(); b.matches = False
        self.assertEqual(finish(b).outcome, 'interrupted')

    def test_unavailable_value_is_not_zero(self):
        b = Backend(); b.fail_value = True
        r = finish(b)
        self.assertEqual((r.outcome,r.value_state,r.value), ('returned','unavailable',None))

    def test_capacity_does_not_resume(self):
        b = Backend(); b.fail_prepare = True
        with self.assertRaises(FinishError): finish(b)
        self.assertFalse(b.resumed)

    def test_primary_and_cleanup_error(self):
        b = Backend(); b.fail_resume = b.fail_cleanup = True
        with self.assertRaisesRegex(TimeoutError, 'primary timeout'): finish(b)
        self.assertEqual(b.cleanup_errors, ['cleanup failure'])

    def test_cleanup_failure_without_primary(self):
        b = Backend(); b.fail_cleanup = True
        with self.assertRaisesRegex(OSError, 'cleanup failure'): finish(b)
