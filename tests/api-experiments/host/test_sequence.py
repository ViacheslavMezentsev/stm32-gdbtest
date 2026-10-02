import unittest
from lab.sequence import CallOrder


class SequenceTests(unittest.TestCase):
    def test_wrong_order_does_not_consume_expected_call(self):
        order = CallOrder(('outer', 'inner'))
        with self.assertRaisesRegex(ValueError, 'expected outer, observed inner'):
            order.observe('inner')
        order.observe('outer')
        order.observe('inner')
        order.complete()

    def test_missing_and_extra_calls_are_rejected(self):
        order = CallOrder(('outer', 'inner'))
        order.observe('outer')
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            order.complete()
        order.observe('inner')
        with self.assertRaisesRegex(ValueError, 'expected <end>'):
            order.observe('inner')
        order.complete()
