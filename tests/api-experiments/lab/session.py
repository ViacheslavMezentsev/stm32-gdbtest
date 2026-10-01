"""Experimental main-thread GDB adapter. No production API/schema changes.

The existing report is accessed only by this bridge, under a dedicated namespace.
RAM access is limited to a consumer-owned region; no MMIO or arbitrary eval reads.
"""

from contextlib import contextmanager
import json
import math
import re
import gdb


class Research:
    def __init__(self, target, ram, evidence_limit=16384):
        self.target = target
        self.ram = ram
        self.evidence_limit = evidence_limit
        self.epoch = 0
        self.last_stop = None
        self.owned = []
        self.evidence = {}

    def __enter__(self):
        gdb.events.cont.connect(self._continued)
        gdb.events.stop.connect(self._stopped)
        self.target.report['research'] = self.evidence
        return self

    def __exit__(self, *args):
        try:
            self.clear()
        finally:
            gdb.events.cont.disconnect(self._continued)
            gdb.events.stop.disconnect(self._stopped)

    def _continued(self, event):
        self.epoch += 1
        self.last_stop = None

    def _stopped(self, event):
        self.last_stop = dict(event=type(event).__name__,
                              breakpoints=[b.number for b in getattr(event, 'breakpoints', ())],
                              signal=getattr(event, 'stop_signal', None), stop_id=self.epoch)

    def record(self, name, data):
        if not re.fullmatch(r'[a-z][a-z0-9_]*', name) or name in self.evidence:
            raise ValueError('Invalid or duplicate evidence name')
        candidate = dict(self.evidence, **{name: data})
        encoded = json.dumps(candidate, allow_nan=False)
        if len(encoded.encode('utf-8')) > self.evidence_limit:
            raise ValueError('Evidence size limit exceeded')
        # Materialize now: later caller mutations cannot change recorded evidence.
        self.evidence[name] = json.loads(json.dumps(data, allow_nan=False))

    def read(self, path):
        if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*|\[\d+\])*', path):
            raise ValueError('Expected a symbol/field/index path, not an expression')
        name = re.match(r'\w+', path)[0]
        symbol = gdb.lookup_global_symbol(name)
        if symbol is None:
            raise ValueError('Missing global symbol: ' + name)
        value = symbol.value()
        for field, index in re.findall(r'\.([A-Za-z_]\w*)|\[(\d+)\]', path[len(name):]):
            if field:
                value = value[field]
            else:
                kind = value.type.strip_typedefs()
                if kind.code != gdb.TYPE_CODE_ARRAY:
                    raise ValueError('Only bounded arrays can be indexed')
                low, high = kind.range()
                if not low <= int(index) <= high:
                    raise ValueError('Array index out of bounds')
                value = value[int(index)]
        return self.freeze(value)

    def freeze(self, value, depth=0):
        if depth > 4:
            raise ValueError('Snapshot depth limit exceeded')
        if value.is_optimized_out:
            raise ValueError('Optimized-out value')
        value.fetch_lazy()
        kind = value.type.strip_typedefs()
        result = dict(type=str(value.type), width=int(kind.sizeof), stop_id=self.epoch)
        if kind.code in (gdb.TYPE_CODE_INT, gdb.TYPE_CODE_BOOL, gdb.TYPE_CODE_CHAR,
                         gdb.TYPE_CODE_ENUM, gdb.TYPE_CODE_PTR):
            result['value'] = int(value)
        elif kind.code == gdb.TYPE_CODE_FLT:
            number = float(value)
            result['value'] = number if math.isfinite(number) else str(number)
        elif kind.code == gdb.TYPE_CODE_ARRAY:
            low, high = kind.range()
            if high - low + 1 > 64:
                raise ValueError('Snapshot array limit exceeded')
            result['value'] = [self.freeze(value[i], depth + 1) for i in range(low, high + 1)]
        elif kind.code == gdb.TYPE_CODE_STRUCT:
            fields = kind.fields()
            if len(fields) > 32 or any(f.name is None for f in fields):
                raise ValueError('Unsupported structure fields')
            result['value'] = {f.name: self.freeze(value[f.name], depth + 1) for f in fields}
        else:
            raise ValueError('Unsupported type: ' + str(kind))
        return result

    def frames(self):
        rows = []
        frame = gdb.newest_frame()
        while frame is not None and len(rows) < 8:
            rows.append(dict(name=frame.name(), pc=int(frame.pc()), type=frame.type(),
                             stop_id=self.epoch))
            frame = frame.older()
        return rows

    def frame(self, index=0):
        frame = gdb.newest_frame()
        for _ in range(index):
            if frame is None:
                raise ValueError('Missing frame')
            frame = frame.older()
        if frame is None or index < 0:
            raise ValueError('Missing frame')
        return self.epoch, frame

    def local(self, handle, name):
        epoch, frame = handle
        if epoch != self.epoch or not frame.is_valid():
            raise ValueError('Stale frame')
        return self.freeze(frame.read_var(name))

    def _range(self, address, size):
        start, length = self.ram
        if type(address) is not int or type(size) is not int or not 0 < size <= 256:
            raise ValueError('Invalid memory request')
        if address < start or address + size > start + length:
            raise ValueError('Outside consumer-owned RAM')

    def read_memory(self, address, size):
        self._range(address, size)
        return bytes(gdb.selected_inferior().read_memory(address, size))

    @contextmanager
    def patch_ram(self, address, data):
        data = bytes(data)
        self._range(address, len(data))
        before = self.read_memory(address, len(data))
        # Preserve the attempted mutation before any write, including write failure.
        key = 'patch_' + str(len(self.evidence))
        self.record(key, dict(address=address, before=before.hex(), requested=data.hex()))
        error = None
        try:
            gdb.selected_inferior().write_memory(address, data)
            yield
        except BaseException as exc:
            error = exc
            raise
        finally:
            try:
                gdb.selected_inferior().write_memory(address, before)
                if self.read_memory(address, len(before)) != before:
                    raise RuntimeError('RAM restoration verification failed')
            except BaseException as cleanup:
                # Do not silently turn an unverified restoration into success.
                raise RuntimeError(f'RAM cleanup failed: {cleanup}; primary: {error}') from cleanup

    def breakpoint(self, location):
        existing = gdb.breakpoints() or ()
        used = sum(len(bp.locations) for bp in existing if bp.is_valid() and bp.enabled
                   and bp.type == gdb.BP_HARDWARE_BREAKPOINT)
        if used >= self.target.profile['breakpoint_limit']:
            raise ValueError('Hardware location budget exhausted')
        try:
            bp = gdb.Breakpoint(location, type=gdb.BP_HARDWARE_BREAKPOINT)
        except gdb.error as exc:
            raise ValueError('Cannot resolve breakpoint location: ' + str(exc)) from exc
        try:
            if bp.pending or len(bp.locations) != 1:
                raise ValueError('Missing or ambiguous breakpoint location')
            if used + len(bp.locations) > self.target.profile['breakpoint_limit']:
                raise ValueError('Hardware location budget exhausted')
        except BaseException:
            bp.delete()
            raise
        self.owned.append(bp)
        return bp

    def run_until(self, location):
        bp = self.breakpoint(location)
        number = bp.number
        expected_pc = int(bp.locations[0].address)
        try:
            self.last_stop = None
            gdb.execute('continue')
            stop = dict(self.last_stop or {})
            stop['pc'] = int(gdb.newest_frame().pc())
            stop['reason'] = ('expected' if number in stop.get('breakpoints', ())
                              and stop['pc'] == expected_pc else 'unexpected')
            self.record('stop_' + str(len(self.evidence)), stop)
            if stop['reason'] != 'expected':
                raise RuntimeError('Unexpected stop: ' + repr(stop))
            return stop
        finally:
            if bp.is_valid():
                bp.delete()

    def clear(self):
        for bp in self.owned:
            if bp.is_valid():
                bp.delete()
        self.owned.clear()
