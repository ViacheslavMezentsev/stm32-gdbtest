"""E2: bounded global RAM snapshots; no C expression evaluation or pointer chasing."""

from dataclasses import dataclass
import math
import re


class ReadError(ValueError):
    def __init__(self, code, path):
        super().__init__(f"{code}: {path}")
        self.code = code
        self.path = path


@dataclass(frozen=True)
class Snapshot:
    path: str
    type_name: str
    size_bytes: int
    value: object
    # Aggregate values are tuples of (field name/index, Snapshot).


class Reader:
    def __init__(self, backend, *, ram_ranges, max_nodes=64, max_bytes=256, max_depth=4):
        if any(type(v) is not int or v <= 0 for v in (max_nodes, max_bytes, max_depth)):
            raise ValueError("limits must be positive integers")
        self.backend = backend
        self.ranges = tuple(ram_ranges)
        if not self.ranges or any(type(a) is not int or type(b) is not int or a < 0 or b <= a
                                  for a, b in self.ranges):
            raise ValueError("explicit RAM ranges are required")
        self.limits = max_nodes, max_bytes, max_depth

    def read(self, path, *, fields=None, count=None):
        if type(path) is not str or len(path) > 256 or not re.fullmatch(
                r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*|\[[0-9]{1,8}\])*", path, re.ASCII):
            raise ReadError("invalid_path", str(path))
        if fields is not None and (type(fields) is not tuple or not fields
                or len(fields) > self.limits[0]
                or any(type(f) is not str or not re.fullmatch(r"[A-Za-z_]\w*", f, re.ASCII) for f in fields)
                or len(set(fields)) != len(fields)):
            raise ReadError("invalid_fields", path)
        if count is not None and (type(count) is not int or not 1 <= count <= self.limits[0]):
            raise ReadError("invalid_count", path)
        if fields is not None and count is not None:
            raise ReadError("conflicting_selection", path)
        budget = [0, 0]

        def describe(value, location):
            info = self.backend.describe(value)
            if info['unavailable']:
                raise ReadError(info['unavailable'], location)
            address, size = info['address'], info['size']
            if address is None or not any(a <= address and address + size <= b for a, b in self.ranges):
                raise ReadError("outside_ram", location)
            return info

        def visit(value, location, depth, selected_fields=None, selected_count=None):
            budget[0] += 1
            if budget[0] > self.limits[0] or depth > self.limits[2]:
                raise ReadError("limit", location)
            info = describe(value, location)
            kind = info['kind']
            if kind not in ('struct', 'array'):
                if selected_fields is not None or selected_count is not None:
                    raise ReadError("wrong_selection", location)
                if kind not in ('int', 'bool', 'float', 'enum'):
                    raise ReadError("unsupported_type", location)
                budget[1] += info['size']
                if budget[1] > self.limits[1]:
                    raise ReadError("limit", location)
                result = self.backend.scalar(value, kind)
                if type(result) is float and not math.isfinite(result):
                    raise ReadError("nonfinite", location)
            else:
                if kind == 'struct':
                    if selected_fields is None or selected_count is not None:
                        raise ReadError("fields_required", location)
                    keys = selected_fields
                else:
                    if selected_fields is not None or selected_count is None:
                        raise ReadError("count_required", location)
                    low, high = info['bounds']
                    if low != 0 or selected_count > high + 1:
                        raise ReadError("array_bounds", location)
                    keys = range(selected_count)
                result = tuple((key, visit(self.backend.child(value, key),
                                          location + (f'[{key}]' if type(key) is int else '.' + key),
                                          depth + 1)) for key in keys)
            return Snapshot(location, info['type'], info['size'], result)

        try:
            self.backend.ensure_stopped()
            tokens = re.findall(r"[A-Za-z_]\w*|[0-9]+", path, re.ASCII)
            value = self.backend.global_value(tokens[0])
            for token in tokens[1:]:
                info = describe(value, path)
                key = int(token) if token.isdecimal() else token
                if type(key) is int:
                    if info['kind'] != 'array' or not info['bounds'][0] <= key <= info['bounds'][1]:
                        raise ReadError("array_bounds", path)
                elif info['kind'] != 'struct':
                    raise ReadError("unsupported_path", path)
                value = self.backend.child(value, key)
            return visit(value, path, 0, fields, count)
        except ReadError:
            raise
        except self.backend.errors as exc:
            raise ReadError("unreadable", path) from exc


class GdbBackend:
    """Global C objects only; invoked on GDB's main thread by the scenario."""
    def __init__(self):
        import gdb
        self.gdb = gdb
        self.errors = (gdb.error, gdb.MemoryError)

    def ensure_stopped(self):
        thread = self.gdb.selected_thread()
        if thread is None or not thread.is_stopped():
            raise ReadError("not_stopped", "")

    def global_value(self, name):
        symbol = self.gdb.lookup_global_symbol(name)
        if symbol is None:
            raise ReadError("missing_symbol", name)
        return symbol.value()

    def describe(self, value):
        gdb = self.gdb
        t = value.type.strip_typedefs()
        kinds = {gdb.TYPE_CODE_INT: 'int', gdb.TYPE_CODE_BOOL: 'bool',
                 gdb.TYPE_CODE_ENUM: 'enum', gdb.TYPE_CODE_FLT: 'float',
                 gdb.TYPE_CODE_STRUCT: 'struct', gdb.TYPE_CODE_ARRAY: 'array'}
        unavailable = 'optimized_out' if value.is_optimized_out else None
        return {'kind': kinds.get(t.code, 'unsupported'), 'type': str(value.type),
                'size': int(t.sizeof), 'address': int(value.address) if value.address is not None else None,
                'bounds': t.range() if t.code == gdb.TYPE_CODE_ARRAY else None,
                'unavailable': unavailable}

    def child(self, value, key):
        return value[key]

    def scalar(self, value, kind):
        if value.is_lazy:
            value.fetch_lazy()
        return float(value) if kind == 'float' else bool(value) if kind == 'bool' else int(value)
