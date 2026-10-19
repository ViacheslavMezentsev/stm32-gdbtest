"""F411-specific FPB remap with write intents, readback and owned-slot removal."""
import struct, threading, json, os
CTRL = 0xe0002000
REMAP = CTRL + 4
COMP = CTRL + 8
DHCSR = 0xe000edf0

class AdapterError(RuntimeError):
    pass

class JsonLog:

    def __init__(self, path):
        self.path = path

    def __call__(self, event):
        with open(self.path, 'a', encoding='utf8') as f:
            f.write(json.dumps(event) + '\n')
            f.flush()
            os.fsync(f.fileno())

class GdbTransport:

    def __init__(self):
        if threading.current_thread() is not threading.main_thread():
            raise AdapterError('GDB main thread required')
        import gdb
        self.gdb = gdb

    def read(self, address, size):
        if threading.current_thread() is not threading.main_thread():
            raise AdapterError('GDB main thread required')
        return bytes(self.gdb.selected_inferior().read_memory(address, size))

    def write(self, address, data):
        if threading.current_thread() is not threading.main_thread():
            raise AdapterError('GDB main thread required')
        self.gdb.selected_inferior().write_memory(address, data)

    def halted(self):
        return bool(struct.unpack('<I', self.read(DHCSR, 4))[0] & 1 << 17)

class Adapter:

    def __init__(self, transport, log):
        self.t = transport
        self.log = log
        self.saved = None
        self.table_saved = None
        self.dirty = False
        self.installed = False
        self.removal = None
        self.primary = None
        self.cleanup_error = None

    def word(self, a):
        b = self.t.read(a, 4)
        if len(b) != 4:
            raise AdapterError('short read')
        return struct.unpack('<I', b)[0]

    def halt_check(self):
        if not self.t.halted():
            raise AdapterError('CPU not halted')

    def snapshot(self):
        return tuple((self.word(CTRL + 4 * i) for i in range(10)))

    def checked_write(self, a, data, mask=0xffffffff):
        self.halt_check()
        # Persist intent before mutation; acknowledgement itself can fail.
        self.log(dict(event='intent', address=a, data=data.hex()))
        self.dirty = True
        self.t.write(a, data)
        actual = self.t.read(a, len(data))
        if len(actual) != len(data):
            raise AdapterError('short readback')
        if len(data) == 4:
            if int.from_bytes(actual, 'little') & mask != int.from_bytes(data, 'little') & mask:
                raise AdapterError('readback mismatch')
        elif actual != data:
            raise AdapterError('readback mismatch')
        self.log(dict(event='verified', address=a, data=actual.hex()))

    def put(self, a, value, mask=0xffffffff):
        self.checked_write(a, struct.pack('<I', value), mask)

    def install(self, block, table, hook, target=None):
        try:
            if self.saved is not None:
                raise AdapterError('single-use adapter')
            self.halt_check()
            base, size = block
            if size != 1024 or base % 8 or (not 0x20000000 <= base < base + size <= 0x20020000):
                raise AdapterError('allocation bounds')
            if table % 32 or not (base <= table and table + 32 <= base + size):
                raise AdapterError('table bounds')
            if target is None or not base <= hook & ~1 < base + size or target % 4:
                raise AdapterError('code alignment/bounds')
            a = self.snapshot()
            b = self.snapshot()
            if a != b:
                raise AdapterError('unstable FPB')
            if a[0] & ~3 != 608:
                raise AdapterError('unsupported FPB')
            if not a[1] & 1 << 29:
                raise AdapterError('remap unsupported')
            if a[7] & 1 or a[9] & 1 or a[8] & 1:
                raise AdapterError('reserved/literal slot occupied')
            for c in a[2:7]:
                if c & 1 and (not c & 0xc0000000):
                    raise AdapterError('existing remap')
            old = self.t.read(table, 32)
            if len(old) != 32 or old != self.t.read(table, 32):
                raise AdapterError('unstable table')
            self.log(dict(event='snapshot', fpb=a, table=table, table_bytes=old.hex()))
            self.saved = a
            self.table_saved = old
            self.table = table
            self.put(CTRL, 2, 1)
            data = bytearray(32)
            struct.pack_into('<I', data, 20, 0xf000f8df)
            struct.pack_into('<I', data, 28, hook | 1)
            self.checked_write(table, bytes(data))
            self.put(REMAP, table & 0x1fffffe0, 0x1fffffe0)
            self.put(COMP + 20, target | 1)
            self.put(COMP + 28, target + 4 | 1)
            self.put(CTRL, 3, 1)
            expected = list(a)
            expected[0] = a[0] & ~3 | 1
            expected[1] = a[1] & ~0x1fffffe0 | table & 0x1fffffe0
            expected[7] = target | 1
            expected[9] = target + 4 | 1
            if self.snapshot() != tuple(expected):
                raise AdapterError('final FPB mismatch')
            self.installed = True
            self.log(dict(event='installed'))
        except Exception as e:
            if self.primary is None:
                self.primary = str(e)
            raise

    def remove(self):
        if self.removal is not None:
            return self.removal
        if not self.dirty:
            self.removal = 'NOT_NEEDED'
            return self.removal
        try:
            self.halt_check()
            if self.saved is None:
                raise AdapterError('missing saved map')
            self.put(CTRL, 2, 1)
            # Restore only our slots; full-map comparison detects foreign changes.
            self.put(COMP + 20, self.saved[7])
            self.put(COMP + 28, self.saved[9])
            self.put(REMAP, self.saved[1] & 0x1fffffe0, 0x1fffffe0)
            self.checked_write(self.table, self.table_saved)
            self.put(CTRL, 2 | self.saved[0] & 1, 1)
            expected = list(self.saved)
            expected[0] &= ~2
            if self.snapshot() != tuple(expected):
                raise AdapterError('restored map mismatch')
            if self.t.read(self.table, 32) != self.table_saved:
                raise AdapterError('restored table mismatch')
            self.log(dict(event='removed'))
            self.installed = False
            self.removal = 'VERIFIED'
        except Exception as e:
            self.cleanup_error = str(e)
            self.removal = 'BLOCKED'
        return self.removal
