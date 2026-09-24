import unittest
from stm32_gdbtest.identity import check_target


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.profile = dict(name="f401cc", mcu="STM32F401CCU6", flash_size=262144,
                            flash_size_address=0x1FFF7A22,
                            identity=dict(address=0xE0042000, mask=0xFFF, value=0x423))
        self.report = {}

    def reader(self, identity=0x10006431, capacity=256):
        def read(address, size):
            self.assertIn((address, size), [(0xE0042000, 4), (0x1FFF7A22, 2)])
            return (identity if size == 4 else capacity).to_bytes(size, "little")
        return read

    def test_warn_preserves_selected_target_and_records_mismatch(self):
        check_target(self.profile, self.reader(), 12224, "warn", self.report)
        self.assertFalse(self.report['identity']['matches'])
        self.assertEqual(self.report['identity']['observed'], 0x431)
        self.assertEqual(self.report['identity']['selected_mcu'], 'STM32F401CCU6')
        self.assertEqual(self.profile['identity']['value'], 0x423)
        self.assertEqual(len(self.report['warnings']), 1)

    def test_strict_rejects_before_flash_capacity_read(self):
        def read(address, size):
            self.assertEqual(size, 4)
            return (0x431).to_bytes(4, 'little')
        with self.assertRaisesRegex(RuntimeError, 'strict'):
            check_target(self.profile, read, 12224, 'strict', self.report)
        self.assertIn('identity', self.report)
        self.assertNotIn('flash_capacity', self.report)

    def test_match_has_no_warning(self):
        check_target(self.profile, self.reader(identity=0x10006423), 262144, 'strict', self.report)
        self.assertTrue(self.report['identity']['matches'])
        self.assertEqual(self.report['warnings'], [])

    def test_actual_capacity_limits_image_even_when_identity_warns(self):
        with self.assertRaisesRegex(RuntimeError, 'exceeds'):
            check_target(self.profile, self.reader(capacity=64), 65537, 'warn', self.report)
        self.assertEqual(self.report['flash_capacity']['observed_bytes'], 65536)

    def test_larger_chip_does_not_expand_profile_limit(self):
        with self.assertRaisesRegex(RuntimeError, 'exceeds'):
            check_target(self.profile, self.reader(capacity=512), 262145, 'warn', self.report)

    def test_capacity_difference_with_fitting_image_warns(self):
        check_target(self.profile, self.reader(capacity=128), 12000, 'warn', self.report)
        self.assertEqual(len(self.report['warnings']), 2)

    def test_unreadable_or_invalid_capacity_never_allows_flash(self):
        for value in (0, 65535):
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'Invalid Flash'):
                check_target(self.profile, self.reader(capacity=value), 12000, 'warn', {})
        def read(address, size):
            if size == 2:
                raise OSError('unreadable')
            return (0x431).to_bytes(4, 'little')
        with self.assertRaisesRegex(OSError, 'unreadable'):
            check_target(self.profile, read, 12000, 'warn', {})
        del self.profile['flash_size_address']
        with self.assertRaisesRegex(RuntimeError, 'lacks'):
            check_target(self.profile, self.reader(), 12000, 'warn', {})

    def test_invalid_policy_is_not_silent_warn(self):
        with self.assertRaises(ValueError):
            check_target(self.profile, self.reader(), 12000, 'ignore', {})
