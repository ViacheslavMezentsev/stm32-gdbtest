"""Failure-path checks for the consumer prototype, without an MCU or GDB."""
import importlib
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
fake = SimpleNamespace()
sys.modules['gdb'] = fake
Research = importlib.import_module('lab.session').Research


class AdapterTests(unittest.TestCase):
    def setUp(self):
        fake.selected_inferior = Mock()
        fake.lookup_global_symbol = Mock()
        fake.BP_HARDWARE_BREAKPOINT = 1
        fake.Breakpoint = Mock()
        fake.error = RuntimeError
        fake.breakpoints = Mock(return_value=[])
        fake.events = SimpleNamespace(cont=Mock(), stop=Mock())
        self.target = SimpleNamespace(report={'status': 'ERROR'}, profile={'breakpoint_limit': 2})
        self.r = Research(self.target, (0x20000000, 32))

    def test_invalid_ranges_never_access_inferior(self):
        for address, size in [(0x1fffffff, 1), (0x2000001f, 2), (0x20000000, 0), (0x20000000, 257)]:
            with self.assertRaises(ValueError):
                self.r.read_memory(address, size)
        fake.selected_inferior.assert_not_called()

    def test_expression_rejected_before_symbol_lookup(self):
        for path in ['f()', 'a=2', '*a', 'a[-1]', 'a;continue']:
            with self.assertRaises(ValueError):
                self.r.read(path)
        fake.lookup_global_symbol.assert_not_called()

    def test_record_rejections_are_atomic(self):
        with self.r:
            self.r.record('first', {'value': 1})
            for name, data, error in [('first', 2, ValueError), ('huge', 'a' * 17000, ValueError),
                                      ('nan', float('nan'), ValueError), ('live', object(), TypeError)]:
                with self.assertRaises(error):
                    self.r.record(name, data)
            self.assertEqual(self.r.evidence, {'first': {'value': 1}})
            self.assertEqual(self.target.report['status'], 'ERROR')

    def test_partial_write_failure_still_restores_and_records_attempt(self):
        inferior = fake.selected_inferior.return_value
        inferior.read_memory.return_value = b'ab'
        inferior.write_memory.side_effect = [RuntimeError('partial write'), None]
        with self.assertRaisesRegex(RuntimeError, 'partial write'):
            with self.r.patch_ram(0x20000000, b'cd'):
                self.fail('must not enter body')
        self.assertEqual(inferior.write_memory.call_args_list[-1].args, (0x20000000, b'ab'))
        self.assertEqual(self.r.evidence['patch_0']['requested'], '6364')

    def test_primary_and_cleanup_failure_both_visible(self):
        inferior = fake.selected_inferior.return_value
        inferior.read_memory.return_value = b'ab'
        inferior.write_memory.side_effect = [None, RuntimeError('restore failed')]
        with self.assertRaisesRegex(RuntimeError, 'restore failed; primary: body failed'):
            with self.r.patch_ram(0x20000000, b'cd'):
                raise ValueError('body failed')

    def test_external_multilocation_budget_prevents_creation(self):
        external = Mock(enabled=True, type=1, locations=[1, 2])
        fake.breakpoints.return_value = [external]
        with self.assertRaisesRegex(ValueError, 'budget'):
            self.r.breakpoint('main')
        fake.Breakpoint.assert_not_called()
        external.delete.assert_not_called()

    def test_ambiguous_point_is_removed(self):
        bp = fake.Breakpoint.return_value
        bp.pending = False
        bp.locations = [1, 2]
        with self.assertRaisesRegex(ValueError, 'ambiguous'):
            self.r.breakpoint('overload')
        bp.delete.assert_called_once()
        self.assertEqual(self.r.owned, [])

    def test_lookup_error_is_normalized(self):
        fake.Breakpoint.side_effect = RuntimeError('No symbol')
        with self.assertRaisesRegex(ValueError, 'Cannot resolve'):
            self.r.breakpoint('absent')

    def test_empty_location_is_removed(self):
        bp = fake.Breakpoint.return_value
        bp.pending = False
        bp.locations = []
        with self.assertRaisesRegex(ValueError, 'Missing'):
            self.r.breakpoint('absent')
        bp.delete.assert_called_once()

    def test_scope_error_releases_only_owned_points_and_handlers(self):
        bp = Mock()
        self.r.owned.append(bp)
        with self.assertRaisesRegex(ValueError, 'body'):
            with self.r:
                raise ValueError('body')
        bp.delete.assert_called_once()
        fake.events.stop.disconnect.assert_called_once()
        fake.events.cont.disconnect.assert_called_once()

    def test_stale_frame_rejected_before_frame_access(self):
        frame = Mock()
        self.r._continued(None)
        with self.assertRaisesRegex(ValueError, 'Stale'):
            self.r.local((0, frame), 'count')
        frame.read_var.assert_not_called()


if __name__ == '__main__':
    unittest.main()
