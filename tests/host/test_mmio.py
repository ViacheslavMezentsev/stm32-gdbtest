"""MMIO: host regression of permissions, journaling and packet counts."""
from dataclasses import replace
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from stm32_gdbtest.mmio import MMIO, GdbTransport, MMIOError, Register
from stm32_gdbtest.records import Journal

class Tests(unittest.TestCase):

    def setUp(self):
        self.reg = Register('P.R', 0x40000000, 32, 'read-write')
        self.journal = Journal()
        self.transport = Mock()
        self.transport.prepare.return_value = object()
        self.transport.read.return_value = b'\x01\x00\x00\x00'
        self.transport.write.return_value = None
        self.catalog = SimpleNamespace(registers={'P.R': self.reg}, sha256='a' * 64)
        self.mmio = MMIO(self.catalog, self.transport, self.journal.record)

    def test_read_write_one_call(self):
        self.assertEqual(self.mmio.read('P.R'), 1)
        self.transport.read.assert_called_once()
        self.transport.write.assert_not_called()
        self.transport.reset_mock()
        r = self.mmio.write('P.R', 42)
        self.assertFalse(r['verified'])
        self.transport.write.assert_called_once()
        self.transport.read.assert_not_called()

    def test_widths(self):
        for width in (8, 16, 32):
            self.transport.reset_mock()
            r = replace(self.reg, width=width)
            self.mmio.write('P.R', 1, override=r, reason='width test')
            self.assertEqual(self.transport.write.call_args.args[-1], 1 .to_bytes(width // 8, 'little'))

    def test_validation_no_transfer(self):
        for reg in [replace(self.reg, address=1), replace(self.reg, width=True), replace(self.reg, address=-1), replace(self.reg, access=[]), replace(self.reg, fields=(('F', -1, 1, 'read-write', None, None, False),))]:
            with self.subTest(reg=reg), self.assertRaises(MMIOError) as cm:
                self.mmio.write('P.R', 1, override=reg, reason='bad')
            self.assertEqual(cm.exception.effect, 'none')
        self.transport.read.assert_not_called()
        self.transport.write.assert_not_called()

    def test_value_refused(self):
        for value in (True, -1, 2 ** 32, 'HAL_GetTick()'):
            with self.assertRaises(MMIOError):
                self.mmio.write('P.R', value)
        self.transport.write.assert_not_called()

    def test_access_policies(self):
        for access in ('read-only', 'writeOnce', 'read-writeOnce'):
            with self.assertRaises(MMIOError):
                self.mmio.write('P.R', 1, override=replace(self.reg, access=access), reason='policy')
        with self.assertRaises(MMIOError):
            self.mmio.read('P.R', override=replace(self.reg, access='write-only'), reason='policy')
        self.transport.write.assert_not_called()
        self.transport.read.assert_not_called()

    def test_effect_consent(self):
        reg = replace(self.reg, read_action='clear')
        with self.assertRaises(MMIOError):
            self.mmio.read('P.R', override=reg, reason='policy')
        self.mmio.read('P.R', override=reg, reason='policy', allow_effects=True)
        self.transport.read.assert_called_once()

    def test_field_restrictions(self):
        for f in [('F', 0, 1, 'read-only', None, None, False), ('F', 0, 1, 'read-write', None, None, True)]:
            with self.assertRaises(MMIOError):
                self.mmio.write('P.R', 1, override=replace(self.reg, fields=(f,)), reason='fields')
        self.transport.write.assert_not_called()

    def test_manual_without_svd(self):
        m = MMIO(None, self.transport, self.journal.record)
        with self.assertRaises(MMIOError):
            m.write('P.R', 1)
        m.write('P.R', 1, override=self.reg, reason='manual SVD correction')
        self.assertTrue(self.journal.records()[0]['data']['override'])

    def test_override_reason_required(self):
        with self.assertRaises(MMIOError):
            self.mmio.write('P.R', 1, override=self.reg)
        self.transport.write.assert_not_called()

    def test_context_failure(self):
        self.transport.prepare.side_effect = ValueError('not halted')
        with self.assertRaises(MMIOError) as cm:
            self.mmio.read('P.R')
        self.assertEqual(cm.exception.effect, 'none')
        self.transport.read.assert_not_called()

    def test_short_response_no_retry(self):
        self.transport.read.return_value = b'\x01'
        with self.assertRaises(MMIOError) as cm:
            self.mmio.read('P.R')
        self.assertEqual(cm.exception.effect, 'unknown')
        self.transport.read.assert_called_once()

    def test_lost_ack(self):
        self.transport.write.side_effect = TimeoutError()
        with self.assertRaises(MMIOError) as cm:
            self.mmio.write('P.R', 1)
        self.assertEqual(cm.exception.stage, 'transport')
        self.transport.write.assert_called_once()
        self.transport.read.assert_not_called()

    def test_journal_before_after(self):
        for limit, calls, effect in [(0, 0, 'none'), (1, 1, 'unknown')]:
            record = Mock(side_effect=[None] * limit + [ValueError('journal full')])
            self.transport.reset_mock()
            m = MMIO(self.catalog, self.transport, record)
            with self.assertRaises(MMIOError) as cm:
                m.write('P.R', 1)
            self.assertEqual(self.transport.write.call_count, calls)
            self.assertEqual(cm.exception.effect, effect)

    def test_rsp_exact_packets(self):
        c = Mock()
        c.send_packet.return_value = b'01000000'
        t = GdbTransport(None, {})
        self.assertEqual(t.read(c, 0x40000000, 4), b'\x01\x00\x00\x00')
        c.send_packet.assert_called_once_with('m40000000,4')
        c.reset_mock()
        c.send_packet.return_value = b'OK'
        t.write(c, 0x40000000, b'\x01\x00')
        c.send_packet.assert_called_once_with('M40000000,2:0100')

    def test_rsp_bad_replies(self):
        for reply in (b'E01', b'', b'01', b'ZZZZZZZZ', None):
            c = Mock()
            c.send_packet.return_value = reply
            with self.assertRaises(ValueError):
                GdbTransport(None, {}).read(c, 0x40000000, 4)
            self.assertEqual(c.send_packet.call_count, 1)

    def test_rsp_context(self):

        class Connection:

            def send_packet(self, p):
                raise AssertionError('no packets in preflight')
        c = Connection()
        g = Mock()
        g.RemoteTargetConnection = Connection
        g.inferiors.return_value = [g.selected_inferior.return_value]
        g.selected_inferior.return_value.connection = c
        g.selected_inferior.return_value.threads.return_value = [SimpleNamespace(is_stopped=lambda: True)]
        g.selected_frame.return_value.architecture.return_value.name.return_value = 'armv7'
        g.execute.return_value = 'The target endianness is set automatically (currently little endian).'
        self.assertIs(GdbTransport(g, {}).prepare(), c)
        g.inferiors.return_value.append(g.selected_inferior.return_value)
        with self.assertRaises(ValueError):
            GdbTransport(g, {}).prepare()
        g.inferiors.return_value.pop()
        g.selected_thread.return_value = None
        with self.assertRaises(ValueError):
            GdbTransport(g, {}).prepare()
    def test_public_error_and_descriptor(self):
        from stm32_gdbtest import MMIOError as PublicError, MMIORegister, ApiError
        self.assertIs(MMIORegister, Register)
        self.assertTrue(issubclass(PublicError, ApiError))
        with self.assertRaises(PublicError) as cm:
            self.mmio.write('P.R', True)
        self.assertEqual(cm.exception.details, dict(operation='mmio.write', code='invalid_value', stage='validation', effect='none'))

    def test_invalid_name_and_consent(self):
        for name, options in [(None, {}), ('', {}), ('P.UNKNOWN', {}), ('P.R', {'allow_effects': 1}), ('P.R', {'reason': '   '})]:
            with self.assertRaises(MMIOError):
                self.mmio.read(name, **options)
        self.transport.prepare.assert_not_called()
        self.transport.read.assert_not_called()

    def test_rsp_context_rejects_running_and_unqualified(self):
        class Connection:
            def send_packet(self, packet):
                raise AssertionError('preflight must not send a packet')
        g = Mock()
        g.RemoteTargetConnection = Connection
        g.inferiors.return_value = [g.selected_inferior.return_value]
        g.selected_inferior.return_value.connection = Connection()
        g.selected_inferior.return_value.threads.return_value = [SimpleNamespace(is_stopped=lambda: True)]
        g.selected_frame.return_value.architecture.return_value.name.return_value = 'armv7'
        g.execute.return_value = 'currently little endian'
        transport = GdbTransport(g, {})
        for response in ('currently big endian', 'auto'):
            g.execute.return_value = response
            with self.assertRaises(ValueError):
                transport.prepare()
        g.execute.return_value = 'currently little endian'
        with patch('stm32_gdbtest.mmio.threading.current_thread', return_value=object()):
            with self.assertRaises(ValueError):
                transport.prepare()
        with self.assertRaises(ValueError):
            GdbTransport(g, {'architecture': 'risc-v'}).prepare()
        g.selected_inferior.return_value.threads.return_value.append(SimpleNamespace(is_stopped=lambda: False))
        with self.assertRaises(ValueError):
            transport.prepare()
        g.selected_inferior.return_value.threads.return_value = [SimpleNamespace(is_stopped=lambda: True)]
        g.selected_inferior.return_value.connection = object()
        with self.assertRaises(ValueError):
            transport.prepare()

if __name__ == '__main__':
    unittest.main()

    def test_reason_without_override_preserves_policy(self):
        self.mmio.write('P.R', 3, reason='restore saved state')
        row = self.journal.records()[0]['data']
        self.assertEqual(row['reason'], 'restore saved state')
        self.assertFalse(row['override'])
        self.catalog.registers['P.R'] = replace(self.reg, access='read-only')
        with self.assertRaises(MMIOError) as cm:
            self.mmio.write('P.R', 1, reason='not permission')
        self.assertEqual(cm.exception.code, 'write_denied')
        self.assertEqual(self.transport.write.call_count, 1)

    def test_transport_error_survives_audit_failure(self):
        primary = TimeoutError('lost ACK')
        self.transport.write.side_effect = primary
        audit = ValueError('journal full')
        m = MMIO(self.catalog, self.transport, Mock(side_effect=[None, audit]))
        with self.assertRaises(MMIOError) as cm:
            m.write('P.R', 1)
        self.assertEqual(cm.exception.code, 'transport_failed')
        self.assertIs(cm.exception.__cause__, primary)
        self.assertEqual(cm.exception.details['audit_error']['message'], 'journal full')
        self.transport.write.assert_called_once()
        self.transport.read.assert_not_called()

    def test_invalid_reason_no_transport(self):
        for reason in ('', '  ', 1, False, []):
            with self.assertRaises(MMIOError) as cm:
                self.mmio.read('P.R', reason=reason)
            self.assertEqual(cm.exception.code, 'invalid_reason')
        self.transport.prepare.assert_not_called()
