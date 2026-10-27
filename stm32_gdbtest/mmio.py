"""Explicit SVD-driven MMIO, one uncached RSP request per accepted operation."""
from dataclasses import asdict
import re
import threading
from stm32_gdbtest.errors import ApiError, error_summary
from stm32_gdbtest.svd import Register, ACCESS, READ, WRITE

class MMIOError(ApiError):

    def __init__(self, code, operation, stage='validation', effect='none'):
        super().__init__(code, operation='mmio.' + operation, code=code, stage=stage, effect=effect)
        self.stage, self.effect = (stage, effect)

class GdbTransport:
    """One send_packet call; GDB transport and server internals remain outside this guarantee."""

    def __init__(self, gdb, profile, state_check=None):
        self.gdb, self.profile = (gdb, profile)
        self.state_check = state_check

    def prepare(self):
        g = self.gdb
        if threading.current_thread() is not threading.main_thread():
            raise ValueError('main_thread_required')
        if self.state_check is not None and not self.state_check():
            raise ValueError("not_stopped")
        if self.profile.get('architecture', 'cortex-m') != 'cortex-m':
            raise ValueError('unsupported_architecture')
        thread = g.selected_thread()
        inferior = g.selected_inferior()
        threads = inferior.threads()
        if thread is None or not threads or (not all((t.is_stopped() for t in threads))):
            raise ValueError('not_stopped')
        connection = inferior.connection
        if not isinstance(connection, g.RemoteTargetConnection) or not callable(getattr(connection, 'send_packet', None)):
            raise ValueError('unqualified_route')
        # Raw packets do not select a process on a multiprocess remote connection.
        if len([i for i in g.inferiors() if i.connection == connection]) != 1:
            raise ValueError('ambiguous_inferior')
        if not g.selected_frame().architecture().name().lower().startswith('arm'):
            raise ValueError('unsupported_architecture')
        if 'little endian' not in g.execute('show endian', to_string=True).lower():
            raise ValueError('unsupported_endian')
        return connection

    def read(self, connection, address, size):
        response = connection.send_packet(f'm{address:x},{size:x}')
        if not isinstance(response, (bytes, bytearray)) or not re.fullmatch(b'[0-9a-fA-F]{' + str(size * 2).encode() + b'}', response):
            raise ValueError('invalid_read_reply')
        return bytes.fromhex(response.decode('ascii'))

    def write(self, connection, address, data):
        response = connection.send_packet(f'M{address:x},{len(data):x}:{data.hex()}')
        if response != b'OK':
            raise ValueError('invalid_write_reply')

def descriptor(reg):
    """Journal-compatible copy; tuples are intentionally converted to lists."""
    data = asdict(reg)
    data['fields'] = [list(f) for f in reg.fields]
    return data

class MMIO:

    def __init__(self, catalog, transport, record):
        self._catalog, self._transport, self._record = (catalog, transport, record)

    def read(self, name, *, allow_effects=False, override=None, reason=None):
        return self._run('read', name, None, allow_effects, override, reason)

    def write(self, name, value, *, allow_effects=False, override=None, reason=None):
        return self._run('write', name, value, allow_effects, override, reason)

    def _run(self, op, name, value, allow_effects, override, reason):

        def reject(code):
            raise MMIOError(code, op)
        if type(name) is not str or not name.strip():
            reject('invalid_register_name')
        if type(allow_effects) is not bool:
            reject('invalid_effect_consent')
        original = self._catalog.registers.get(name) if self._catalog else None
        reg = original
        if override is not None:
            if type(override) is not Register or type(reason) is not str or (not reason.strip()):
                reject('invalid_override')
            reg = override
        elif reason is not None and (type(reason) is not str or not reason.strip()):
            reject('invalid_reason')
        if reg is None:
            reject('missing_svd' if self._catalog is None else 'unknown_register')
        if reg.name != name:
            reject('override_name_mismatch')
        if type(reg.address) is not int or type(reg.width) is not int or reg.width not in (8, 16, 32):
            reject('invalid_descriptor')
        size = reg.width // 8
        if not 0 <= reg.address <= 2 ** 32 - size or reg.address % size:
            reject('invalid_address')
        if (type(reg.access) is not str
                or reg.access not in ACCESS
                or type(reg.read_action) not in (str, type(None))
                or (reg.read_action not in READ | {None})
                or (type(reg.write_effect) not in (str, type(None)))
                or (reg.write_effect not in WRITE | {None})):
            reject('invalid_policy')
        if type(reg.constraint) is not bool or type(reg.fields) is not tuple:
            reject('invalid_descriptor')
        mask = 0
        names = set()
        for f in reg.fields:
            if (type(f) is not tuple
                    or len(f) != 7
                    or type(f[0]) is not str
                    or (not f[0])
                    or (f[0] in names)
                    or (type(f[1]) is not int)
                    or (type(f[2]) is not int)
                    or (f[1] < 0)
                    or (f[2] <= 0)
                    or (f[1] + f[2] > reg.width)
                    or (type(f[3]) is not str)
                    or (f[3] not in ACCESS)
                    or (type(f[4]) not in (str, type(None)))
                    or (f[4] not in READ | {None})
                    or (type(f[5]) not in (str, type(None)))
                    or (f[5] not in WRITE | {None})
                    or (type(f[6]) is not bool)):
                reject('invalid_field')
            bits = ((1 << f[2]) - 1) << f[1]
            if mask & bits:
                reject('overlapping_fields')
            mask |= bits
            names.add(f[0])
        permissions = [reg.access, *[f[3] for f in reg.fields]]
        if op == 'read' and any((x in ('write-only', 'writeOnce') for x in permissions)):
            reject('read_denied')
        if op == 'write':
            if type(value) is not int or not 0 <= value < 2 ** reg.width:
                reject('invalid_value')
            if 'read-only' in permissions:
                reject('write_denied')
            if any(('Once' in x for x in permissions)):
                reject('once_history_unknown')
            if reg.constraint or any((f[6] for f in reg.fields)):
                reject('constraint_unsupported')
        effect = reg.read_action if op == 'read' else reg.write_effect
        if (effect or any((f[4 if op == 'read' else 5] for f in reg.fields))) and (not allow_effects):
            reject('effect_consent_required')
        try:
            connection = self._transport.prepare()
        except Exception as exc:
            raise MMIOError('unqualified_context', op) from exc
        entry = dict(operation=op, name=name, original=descriptor(original) if original else None, effective=descriptor(reg), svd_sha256=self._catalog.sha256 if self._catalog else None, override=override is not None, reason=reason, allow_effects=allow_effects)
        if op == 'write':
            entry['value'] = value
        try:
            self._record('mmio.attempt', entry)
        except Exception as exc:
            raise MMIOError('journal_unavailable', op, 'audit') from exc
        try:
            if op == 'read':
                raw = self._transport.read(connection, reg.address, size)
                if type(raw) is not bytes or len(raw) != size:
                    raise ValueError('incomplete_read')
                result = int.from_bytes(raw, 'little')
            else:
                ack = self._transport.write(connection, reg.address, value.to_bytes(size, 'little'))
                if ack is not None:
                    raise ValueError('invalid_ack')
                result = dict(address=reg.address, width=reg.width, value=value, acknowledged=True, verified=False)
        except Exception as exc:
            error = MMIOError('transport_failed', op, 'transport', 'unknown')
            try:
                self._record('mmio.result', dict(operation=op, name=name, status='ERROR', effect='unknown'))
            except Exception as audit:
                error.details['audit_error'] = error_summary(audit)
            raise error from exc
        try:
            self._record('mmio.result', dict(operation=op, name=name, status='completed', result=result))
        except Exception as exc:
            raise MMIOError('journal_unavailable', op, 'audit', 'unknown') from exc
        return result
