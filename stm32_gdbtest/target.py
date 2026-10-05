"""Target API. Imported only inside GDB's main Python thread."""

import hashlib
import os
import re

import gdb
from stm32_gdbtest.errors import ApiError, CheckFailed, fail  # noqa: F401
from stm32_gdbtest.records import Journal
from stm32_gdbtest.configuration import (DEFAULTS, EXECUTE_OUTPUT_LIMIT, FRAMES_LIMIT,
                                           MEMORY_LIMIT, RESET_COMMAND, freeze)
from stm32_gdbtest import values
from stm32_gdbtest.run_profile import Profile

_CLONE = re.compile(r"\s*\[clone [^\]]*\]")
_FUNCTION_NAME = re.compile(r"[A-Za-z_]\w*")
_SECTION = re.compile(r" in section (\S+)")
# Writable SRAM window shared by `write` verification and `write_memory` (ТЗ API 4.6, 4.16).
SRAM_WINDOW = (0x20000000, 0x20100000)


def _number(value):
    """A real number that is not a bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)



# Converting a GDB value can fail with a plain Python error as well; the tuple is built per call so
# that importing this module does not depend on a loaded GDB.
def conversion_errors(module):
    return (module.error, TypeError, ValueError, OverflowError)

def function_name(name):
    """Plain function name of a frame (ТЗ 5.10.7).

    GDB may name a frame by its ELF symbol instead of DWARF, as GCC/LTO emits it:
    `HmiManager::init() [clone .constprop.0]`, `ParamRegistry::print() const`. Clone
    suffixes, trailing qualifiers and the parameter list are removed.
    """
    if name is None:
        return None
    name = _CLONE.sub("", name).strip()
    while name.endswith((" const", " volatile")):
        name = name.rsplit(" ", 1)[0]
    if name.endswith(")"):
        depth = 0
        for index in range(len(name) - 1, -1, -1):
            depth += {")": 1, "(": -1}.get(name[index], 0)
            if depth == 0:
                name = name[:index]
                break
    return name.strip()


class Point:
    """A set point and its state (ТЗ API 4.4).

    The object owns one native `gdb.Breakpoint`, supports the context manager (`with` removes the
    point on exit) and keeps the number of stops observed for it.
    """

    def __init__(self, native, location, owner=None, temporary=False, condition=None, ignore_count=0):
        self._native = native
        # The number is captured now: GDB refuses attribute access on a deleted breakpoint.
        self._number = native.number
        self.location = location
        # The creation parameters decide whether a later request may share this point (ТЗ API 4.4.2).
        self.temporary = temporary
        self._condition = condition
        self.ignore_count = ignore_count
        # A watchpoint created by address reports its expression instead of a location.
        self.watch = False
        self.watched = None
        self.snapshot = None
        self.hit_count = 0
        self._owner = owner
        self._removed = False

    @property
    def id(self):
        return self._number

    number = id

    @property
    def addresses(self):
        """Resolved addresses as integers; a deleted point reports none instead of raising.

        GDB lists `gdb.BreakpointLocation` objects; their `address` is what a scenario compares and records.
        """
        if self._removed:
            return []
        try:
            locations = list(self._native.locations)
        except (AttributeError, gdb.error, RuntimeError):
            return []
        addresses = []
        for location in locations:
            address = getattr(location, "address", location)
            try:
                addresses.append(int(address))
            except (TypeError, ValueError):
                continue
        return addresses

    @property
    def active(self):
        if self._removed:
            return False
        try:
            return self._native.is_valid() and self._native.enabled
        except RuntimeError:
            return False

    @property
    def enabled(self):
        """The point exists and is not disabled; a disabled point keeps its counter."""
        return self.active

    @property
    def condition(self):
        return self._condition

    @condition.setter
    def condition(self, condition):
        """Replace the stop condition of the live point; None removes it (ТЗ API 4.4.3)."""
        if condition is not None and (type(condition) is not str or not condition.strip()):
            fail("point", "validation", "none", "invalid_condition",
                 "condition must be a non-empty string or None", point=self._number, condition=condition)
        self._require_valid("condition")
        try:
            self._native.condition = condition
        except (gdb.error, RuntimeError) as cause:
            fail("point", "command", "none", "command_failed", f"condition rejected: {condition}",
                 cause=cause, point=self._number, condition=condition)
        self._condition = condition

    def enable(self):
        """Activate a disabled point; the hardware budget counts only active points (ТЗ API 4.4.3)."""
        self._require_valid("enable")
        if self.active:
            return self
        owner = self._owner
        if owner is not None:
            limit = owner.profile["breakpoint_limit"]
            if sum(point.active for point in owner.owned) >= limit:
                fail("point", "validation", "none", "limit_exceeded",
                     "profile hardware breakpoint budget exhausted", point=self._number, limit=limit)
        self._native.enabled = True
        return self

    def disable(self):
        """Keep the point and its counter but stop it from halting the target (ТЗ API 4.4.3)."""
        self._require_valid("disable")
        self._native.enabled = False
        return self

    def _require_valid(self, action):
        try:
            valid = not self._removed and self._native.is_valid()
        except RuntimeError:
            valid = False
        if not valid:
            fail("point", "validation", "none", "point_removed", f"{action} on a removed point",
                 point=self._number)

    def remove(self):
        """Delete the point and forget it; a repeated removal is not an error."""
        self._removed = True
        try:
            valid = self._native.is_valid()
        except RuntimeError:
            valid = False
        if valid:
            self._native.delete()
        if self._owner is not None:
            self._owner.owned[:] = [point for point in self._owner.owned if point is not self]

    def is_valid(self):
        """0.1/0.2 `gdb.Breakpoint` spelling of `active` (ТЗ API 4.4.1)."""
        return self.active

    def delete(self):
        """0.1/0.2 `gdb.Breakpoint` spelling of `remove()` (ТЗ API 4.4.1)."""
        self.remove()

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        self.remove()
        return False

    def __repr__(self):
        return f"Point(id={self._native.number}, location={self.location!r}, active={self.active})"


class Target:
    def __init__(self, report, profile, configuration=None, context=None):
        self.report = report
        context = dict(context or {})
        self.profile = Profile(profile, configuration, case=context.get("case"), stand=context.get("stand"),
                               gdb=self._gdb_facts())
        self._config = configuration.config if configuration else freeze(dict(
            target=profile, api=dict(schema=1, records=dict(DEFAULTS)), image=None))
        limits = self._config['api']['records']
        self._journal = Journal(**{key: limits[key] for key in DEFAULTS})
        self.owned = []
        self.stops = []
        gdb.events.stop.connect(self.on_stop)

    @staticmethod
    def _gdb_facts():
        """What this GDB offers, known before the first stop (ТЗ API 4.14.2)."""
        kind = getattr(gdb, "Type", None)
        return dict(version=getattr(gdb, "VERSION", None),
                    stop_details=None,
                    value_history=callable(getattr(gdb, "history_count", None)),
                    type_is_signed=kind is not None and hasattr(kind, "is_signed"))

    def record(self, name, data):
        return self._journal.record(name, data)

    def records(self, name=None):
        return self._journal.records(name)

    def on_stop(self, event):
        # Capture primitive values now: temporary breakpoint objects expire after stop.
        numbers = [bp.number for bp in getattr(event, "breakpoints", ())]
        if self.profile.gdb.get("stop_details") is None:
            self.profile._observe_gdb(stop_details=isinstance(getattr(event, "details", None), dict))
        self.stops.append({"type": type(event).__name__, "breakpoints": numbers,
                           "signal": getattr(event, "stop_signal", None),
                           # GDB 14 events carry no `details`; recording it shows which evidence a
                           # classification below rests on (ТЗ API 4.5).
                           "details_available": isinstance(getattr(event, "details", None), dict),
                           "native_reason": getattr(event, "details", {}).get("reason")
                           if isinstance(getattr(event, "details", {}), dict) else None})
        for point in self.owned:
            if point.id in numbers:
                point.hit_count += 1

    def check(self, name, actual, expected):
        """Record one comparison and fail the scenario on a mismatch (ТЗ API 4.1)."""
        self._verdict(name, actual, expected, actual == expected, f"expected {expected!r}")

    def _verdict(self, name, actual, expected, passed, wanted, kind=None):
        entry = dict(name=name, actual=actual, expected=expected, passed=passed)
        if kind is not None:
            entry["kind"] = kind
        self.report["checks"].append(entry)
        print(f"{'PASS' if passed else 'FAIL'} {name}: {actual!r}, {wanted}")
        if not passed:
            raise CheckFailed(name, actual=actual, expected=expected)

    def _check_name(self, name):
        if type(name) is not str or not name:
            self._fail("check", "validation", "none", "invalid_name",
                       "check name must be a non-empty string", name=name)

    def check_range(self, name, actual, low, high):
        """Pass when low <= actual <= high; the report keeps the value and both bounds (ТЗ API 4.1.2)."""
        self._check_name(name)
        if not (_number(low) and _number(high)) or low > high:
            self._fail("check", "validation", "none", "invalid_bounds",
                       "bounds must be numbers with low <= high", name=name, low=low, high=high)
        passed = _number(actual) and low <= actual <= high
        self._verdict(name, actual, dict(low=low, high=high), passed, f"expected {low!r}..{high!r}", "range")

    def check_near(self, name, actual, expected, tolerance):
        """Pass when |actual - expected| <= tolerance (ТЗ API 4.1.2)."""
        self._check_name(name)
        if not _number(expected) or not _number(tolerance) or tolerance < 0:
            self._fail("check", "validation", "none", "invalid_tolerance",
                       "expected must be a number and tolerance a non-negative number",
                       name=name, expected=expected, tolerance=tolerance)
        passed = _number(actual) and abs(actual - expected) <= tolerance
        self._verdict(name, actual, dict(value=expected, tolerance=tolerance), passed,
                      f"expected {expected!r} ± {tolerance!r}", "near")

    def check_in(self, name, actual, options):
        """Pass when actual equals one of the options (ТЗ API 4.1.2)."""
        self._check_name(name)
        if not isinstance(options, (list, tuple, set, frozenset)) or not options:
            self._fail("check", "validation", "none", "invalid_options",
                       "options must be a non-empty list, tuple or set", name=name)
        choices = list(options)
        self._verdict(name, actual, {"in": choices}, actual in choices, f"expected one of {choices!r}", "in")

    def check_table(self, rows):
        """Check rows of (name, actual, expected); string cells are GDB expressions (ТЗ API 4.1.3).

        Each row is evaluated and checked in order, so the first mismatch stops the scenario like
        `check`. Returns the number of checked rows.
        """
        if not isinstance(rows, (list, tuple)) or not rows:
            self._fail("check", "validation", "none", "invalid_rows", "rows must be a non-empty list")
        for row in rows:
            if not isinstance(row, (list, tuple)) or len(row) != 3:
                self._fail("check", "validation", "none", "invalid_rows",
                           "each row must be (name, actual, expected)", row=row)
            self._check_name(row[0])
        for name, actual, expected in rows:
            if isinstance(actual, str):
                actual = self.evaluate(actual)
            if isinstance(expected, str):
                expected = self.evaluate(expected)
            self.check(name, actual, expected)
        return len(rows)

    def value(self, expression):
        value = gdb.parse_and_eval(expression)
        if value.is_optimized_out:
            raise RuntimeError(f"Value optimized out: {expression}")
        value.fetch_lazy()
        return int(value)

    def fields(self, expression, expected):
        """Compare scalar fields separately; expected values are C expressions or integers."""
        for field, reference in expected.items():
            actual = self.value(f"({expression}).{field}")
            wanted = self.value(reference) if isinstance(reference, str) else reference
            self.check(f"{expression}.{field}", actual, wanted)

    def frames(self, limit=None):
        """Frame chain from the innermost frame outwards (ТЗ API 4.5).

        Each entry carries its depth, function name, program counter and method; without an explicit
        `limit` the value from `api.toml` is used, then the agreed default.
        """
        if limit is None:
            limit = self._frames_limit()
        if type(limit) is not int or limit < 1:
            self._fail("frames", "validation", "none", "invalid_limit",
                       "limit must be a positive integer", limit=limit)
        frame = gdb.newest_frame()
        if frame is None or not frame.is_valid():
            self._fail("frames", "validation", "none", "no_frame",
                       "a valid frame is required", limit=limit)
        chain = []
        while frame is not None and len(chain) < limit:
            try:
                valid = frame.is_valid()
            except RuntimeError:
                valid = False
            if not valid:
                break
            chain.append(self._frame_entry(frame, len(chain)))
            frame = frame.older()
        return dict(operation="frames", frames=chain, count=len(chain), limit=limit,
                    complete=len(chain) < limit)

    def _frames_limit(self):
        """Configured frame limit, falling back to the agreed default."""
        try:
            limit = self._config["api"]["frames"]["limit"]
        except (KeyError, TypeError):
            return FRAMES_LIMIT
        if type(limit) is not int or limit < 1:
            self._fail("frames", "validation", "none", "invalid_limit",
                       "frames.limit must be a positive integer", limit=limit)
        return limit

    def _frame_entry(self, frame, depth):
        """One frame as a plain dictionary; a broken accessor does not hide the chain."""
        try:
            name = function_name(frame.name())
        except conversion_errors(gdb) + (RuntimeError,):
            name = None
        try:
            pc = int(frame.pc())
        except conversion_errors(gdb) + (RuntimeError,):
            pc = None
        kind = getattr(frame, "type", None)
        try:
            code = kind() if callable(kind) else None
        except conversion_errors(gdb) + (RuntimeError,):
            code = None
        if code is None:
            method = "unknown"
        elif code == getattr(gdb, "NORMAL_FRAME", object()):
            method = "normal"
        elif code == getattr(gdb, "SIGTRAMP_FRAME", object()):
            method = "signal"
        else:
            method = "other"
        return dict(depth=depth, name=name, pc=pc, method=method)

    def evaluate(self, expression, *, as_type=None):
        """Evaluate an expression in the halted program and convert the result (ТЗ API 4.3).

        `as_type` may be `int`, `float`, `bool` (or their names); without it the declared type of the
        value decides. The conversion happens after the expression executed, so a wrong type is
        reported as a failure of the result, not of the expression.
        """
        if type(expression) is not str or not expression.strip():
            self._fail("eval", "validation", "none", "invalid_expression",
                       "expression must be a non-empty string", expression=expression)
        requested = self._as_type(as_type)
        try:
            value = gdb.parse_and_eval(expression)
        except gdb.error as cause:
            self._fail("eval", "command", "unknown", "command_failed",
                       f"{expression} failed", cause=cause, expression=expression)
        if getattr(value, "is_optimized_out", False):
            self._fail("eval", "observe", "none", "optimized_out",
                       f"value is optimized out: {expression}", expression=expression)
        try:
            value.fetch_lazy()
            plain = values.value_to_plain(value, expression, gdb)
        except conversion_errors(gdb) as cause:
            self._fail("eval", "readback", "none", "conversion_failed",
                       f"conversion failed for {expression}", cause=cause, expression=expression)
        kind = plain.__class__.__name__ if plain is not None else None
        if requested is None:
            return plain
        try:
            converted = requested(plain)
        except (TypeError, ValueError) as cause:
            self._fail("eval", "readback", "none", "unsupported_type",
                       f"cannot convert the result of {expression} to {requested.__name__}",
                       cause=cause, expression=expression, value=plain)
        self.report.setdefault("evaluations", []).append(
            dict(operation="eval", expression=expression, value=converted,
                 value_type=requested.__name__, declared=kind))
        return converted

    def _as_type(self, as_type):
        """Normalize the requested result type; None keeps the declared type."""
        if as_type is None:
            return None
        mapping = {int: int, float: float, bool: bool, "int": int, "float": float, "bool": bool}
        if isinstance(as_type, str) and as_type in mapping:
            return mapping[as_type]
        if as_type in mapping:
            return mapping[as_type]
        self._fail("eval", "validation", "none", "unsupported_type",
                   "as_type must be int, float or bool", as_type=as_type)

    def registers(self, *names, frame=None):
        """Read named registers of a frame as one dictionary (ТЗ API 4.4).

        `pc` prefers the frame accessor because a forced return can leave the register stale; other
        names are read by name and masked by the declared width of the register.
        """
        if not names:
            self._fail("registers", "validation", "none", "invalid_names",
                       "at least one register name is required")
        for name in names:
            if type(name) is not str or not name:
                self._fail("registers", "validation", "none", "invalid_names",
                           "register names must be non-empty strings", name=name)
        target_frame = frame if frame is not None else gdb.newest_frame()
        if target_frame is None or not target_frame.is_valid():
            self._fail("registers", "validation", "none", "no_frame",
                       "a valid frame is required", names=list(names))
        result = {}
        for name in names:
            result[name] = self._read_register(target_frame, name)
        return result

    def _read_register(self, frame, name):
        """Value of one register, masked by its declared width."""
        if name == "pc":
            try:
                return int(frame.pc())
            except conversion_errors(gdb) + (RuntimeError,) as cause:
                self._fail("registers", "observe", "none", "read_failed",
                           "pc is not available in this frame", cause=cause, register=name)
        try:
            value = frame.read_register(name)
        except conversion_errors(gdb) + (RuntimeError,) as cause:
            self._fail("registers", "observe", "none", "read_failed",
                       f"register {name} is not available", cause=cause, register=name)
        kind = values.unqualified_type(value.type)
        size = getattr(kind, "sizeof", None)
        number = int(value)
        if size:
            number &= (1 << (int(size) * 8)) - 1
        return number

    def symbol(self, name):
        """Address, size, type and section of a global or static symbol (ТЗ API 4.15)."""
        if type(name) is not str or not name.strip():
            self._fail("symbol", "validation", "none", "invalid_name",
                       "symbol name must be a non-empty string", name=name)
        found = None
        for lookup in ("lookup_global_symbol", "lookup_static_symbol"):
            finder = getattr(gdb, lookup, None)
            if finder is None:
                continue
            try:
                found = finder(name)
            except gdb.error:
                found = None
            if found is not None:
                break
        if found is None:
            self._fail("symbol", "observe", "none", "symbol_absent",
                       f"no global or static symbol {name}", name=name)
        try:
            value = found.value()
            function = bool(getattr(found, "is_function", False))
            address = int(value.address) if value.address is not None else int(value)
        except conversion_errors(gdb) + (RuntimeError,) as cause:
            self._fail("symbol", "observe", "none", "no_address", f"{name} has no address",
                       cause=cause, name=name)
        size = self._function_size(found, address) if function else getattr(found.type, "sizeof", None)
        try:
            where = gdb.execute(f"info symbol {address:#x}", to_string=True)
        except gdb.error:
            where = ""
        section = _SECTION.search(where)
        return dict(operation="symbol", name=name, kind="function" if function else "variable",
                    address=address, size=int(size) if size is not None else None,
                    type=str(found.type), section=section.group(1) if section else None)

    @staticmethod
    def _function_size(symbol, address):
        """Code size of a function from its lexical block, or None when GDB has no block."""
        try:
            block = gdb.block_for_pc(address)
        except (gdb.error, RuntimeError):
            return None
        while block is not None and block.function is None:
            block = block.superblock
        if block is None:
            return None
        return int(block.end) - int(block.start)

    def _memory_window(self, address, size, writable):
        """Raise unless [address, address+size) lies inside SRAM, or flash for reads."""
        windows = [SRAM_WINDOW]
        if not writable:
            start = self.profile.get("flash_start")
            if _number(start) and _number(self.profile.get("flash_size")):
                windows.append((start, start + self.profile["flash_size"]))
        if not any(low <= address and address + size <= high for low, high in windows):
            self._fail("memory", "validation", "none", "outside_window",
                       "the block must lie in SRAM" + ("" if writable else " or the profile flash"),
                       address=address, size=size)

    def memory(self, address, size):
        """Raw bytes of a memory block in SRAM or the profile flash (ТЗ API 4.16).

        Peripheral addresses are refused: a read there may change the device state.
        """
        if type(address) is not int or address < 0 or type(size) is not int or not 1 <= size <= MEMORY_LIMIT:
            self._fail("memory", "validation", "none", "invalid_block",
                       f"address must be a non-negative integer and size 1..{MEMORY_LIMIT}",
                       address=address, size=size)
        self._memory_window(address, size, writable=False)
        try:
            return bytes(gdb.selected_inferior().read_memory(address, size))
        except (gdb.error, getattr(gdb, "MemoryError", gdb.error), RuntimeError) as cause:
            self._fail("memory", "command", "none", "read_failed", f"cannot read {size} bytes at {address:#x}",
                       cause=cause, address=address, size=size)

    def write_memory(self, address, data, *, verify=True):
        """Write raw bytes into SRAM and verify the read-back (ТЗ API 4.16)."""
        if type(address) is not int or address < 0 or not isinstance(data, (bytes, bytearray)) \
                or not 1 <= len(data) <= MEMORY_LIMIT:
            self._fail("memory", "validation", "none", "invalid_block",
                       f"address must be a non-negative integer and data 1..{MEMORY_LIMIT} bytes",
                       address=address, size=len(data) if isinstance(data, (bytes, bytearray)) else None)
        if type(verify) is not bool:
            self._fail("memory", "validation", "none", "invalid_verify", "verify must be a bool")
        data = bytes(data)
        self._memory_window(address, len(data), writable=True)
        inferior = gdb.selected_inferior()
        try:
            before = bytes(inferior.read_memory(address, len(data)))
            inferior.write_memory(address, data)
        except (gdb.error, getattr(gdb, "MemoryError", gdb.error), RuntimeError) as cause:
            self._fail("memory", "command", "unknown", "write_failed",
                       f"cannot write {len(data)} bytes at {address:#x}", cause=cause, address=address)
        after = bytes(inferior.read_memory(address, len(data))) if verify else None
        self.report.setdefault("mutations", []).append(
            dict(expression=f"memory[{address:#x}:{address + len(data):#x}]", value=data.hex(),
                 before=before.hex(), after=after.hex() if after is not None else None))
        if verify and after != data:
            self._fail("memory", "readback", "applied", "verification_failed",
                       f"read-back differs at {address:#x}", address=address,
                       expected=data.hex(), actual=after.hex())
        return dict(operation="write_memory", address=address, size=len(data), verified=verify)

    def locals(self, frame=None):
        """Local variables of a frame: inner blocks shadow outer ones (ТЗ API 4.17)."""
        return self._frame_symbols("locals", frame, arguments=False)

    def arguments(self, frame=None):
        """Arguments of the function of a frame (ТЗ API 4.17)."""
        return self._frame_symbols("arguments", frame, arguments=True)

    def _select_frame(self, operation, frame):
        """None is the newest frame, an int is a depth counted from it, a gdb.Frame is used as is."""
        if frame is None or type(frame) is int:
            depth = frame or 0
            if depth < 0:
                self._fail(operation, "validation", "none", "invalid_frame", "depth must be >= 0", frame=frame)
            current = gdb.newest_frame()
            for _ in range(depth):
                current = current.older() if current is not None else None
        else:
            current = frame
        try:
            valid = current is not None and current.is_valid()
        except RuntimeError:
            valid = False
        if not valid:
            self._fail(operation, "validation", "none", "no_frame", "a valid frame is required", frame=frame)
        return current

    def _frame_symbols(self, operation, frame, *, arguments):
        current = self._select_frame(operation, frame)
        try:
            block = current.block()
        except (gdb.error, RuntimeError) as cause:
            self._fail(operation, "observe", "none", "no_debug_info",
                       "the frame has no debug information", cause=cause)
        result, missing = {}, []
        while block is not None:
            for symbol in block:
                wanted = symbol.is_argument if arguments else (symbol.is_variable and not symbol.is_argument)
                if not wanted or symbol.name in result or symbol.name in missing:
                    continue
                try:
                    value = symbol.value(current)
                    if getattr(value, "is_optimized_out", False):
                        missing.append(symbol.name)
                        continue
                    value.fetch_lazy()
                    result[symbol.name] = values.value_to_plain(value, symbol.name, gdb)
                except conversion_errors(gdb) + (RuntimeError,):
                    missing.append(symbol.name)
            if block.function is not None:
                break
            block = block.superblock
        try:
            name = function_name(current.name())
        except conversion_errors(gdb) + (RuntimeError,):
            name = None
        return dict(operation=operation, function=name, values=result, unavailable=missing)

    def read(self, path, *, fields=None, start=0, count=None):
        """Read a scalar, string, array slice, struct or single fields (ТЗ API 4.2).

        Scalar and string reads return plain Python values; an array returns a list, a struct returns
        a dict of plain values, and `fields` returns a dict of the requested members. Slices apply to
        arrays only and are bounded by the declared range.
        """
        if type(path) is not str or not path:
            values.invalid_path(path)
        if fields is not None:
            return self._read_fields(path, fields)
        if start or count is not None:
            try:
                value = gdb.parse_and_eval(path)
            except gdb.error as cause:
                values.conversion_failed(path, path, cause)
            if values.type_code(value, gdb) != values.type_constant("TYPE_CODE_ARRAY", gdb):
                self._fail("read", "validation", "none", "unsupported_type",
                           f"slices apply to arrays only: {path}", path=path)
            try:
                return [values.value_to_plain(element, f"{path}[{index}]", gdb)
                        for index, element in enumerate(values.array_elements(
                            value, path, start=start, count=count, gdb=gdb))]
            except gdb.error as cause:
                values.conversion_failed(path, path, cause)
        return self._read_value(path, path)

    def _read_fields(self, path, members):
        """Read named members of a compound object; members are names or {name: type} hints."""
        if type(members) is not dict or not members:
            self._fail("read", "validation", "none", "invalid_fields",
                       "fields must be a non-empty mapping", path=path, fields=members)
        result = {}
        for field in members:
            if type(field) is not str or not field:
                self._fail("read", "validation", "none", "invalid_fields",
                           f"invalid field name {field!r}", path=path)
            result[field] = self._read_value(f"({path}).{field}", f"{path}.{field}")
        return result

    def _read_value(self, expression, path):
        """Parse one expression and convert it; GDB refusals become ApiError diagnostics."""
        try:
            value = gdb.parse_and_eval(expression)
        except gdb.error as cause:
            values.conversion_failed(path, expression, cause)
        if getattr(value, "is_optimized_out", False):
            values.optimized_out(path, expression)
        try:
            value.fetch_lazy()
            return values.value_to_plain(value, path, gdb)
        except conversion_errors(gdb) as cause:
            values.conversion_failed(path, expression, cause)

    def _fail(self, operation, stage, effect, code, message, **details):
        """Raise ApiError through the shared validator, keeping the vocabulary in one place."""
        fail(operation, stage, effect, code, message, **details)

    def write(self, path, value, *, verify=True):
        """Write a plain value into a scalar object and verify it (ТЗ API 4.6)."""
        if type(path) is not str or not path:
            self._fail("write", "validation", "none", "invalid_path",
                       "path must be a non-empty string", path=path)
        if type(verify) is not bool:
            self._fail("write", "validation", "none", "invalid_verify",
                       "verify must be a bool", path=path, verify=verify)
        literal = values.argument_literal(value)
        if literal is None:
            self._fail("write", "validation", "none", "unsupported_value",
                       "value must be a finite number, a bool or a GDB expression", path=path, value=value)
        before = self._read_value(path, path)
        scoped, address = self._verify_scope(path)
        self._write_expression(path, literal)
        after = self._read_value(path, path) if (verify and scoped) else None
        # An expression value (an enum constant, a macro) is compared by what it evaluates to.
        expected = self._read_value(f"({literal})", literal) if (verify and scoped and type(value) is str) \
            else value
        entry = dict(expression=path, value=value, before=before, after=after)
        if verify and not scoped:
            # A peripheral register keeps its own meaning on read, so the write is recorded without
            # claiming a verification that this address cannot support.
            entry["verified"] = False
            entry["verify_scope"] = "outside"
            entry["address"] = address
        self.report.setdefault("mutations", []).append(entry)
        if verify and scoped and after != expected:
            values.verification_failed(path, value, after)
        return dict(operation="write", path=path, value=value, before=before, after=after,
                    verified=bool(verify and scoped), verify_scope="declared" if scoped else "outside")

    def _verify_scope(self, path):
        """Whether a read-compare is meaningful here: an addressable object in the SRAM window."""
        try:
            value = gdb.parse_and_eval(path)
        except gdb.error:
            return False, None
        address = getattr(value, "address", None)
        if address is None:
            return False, None
        address = int(address)
        return SRAM_WINDOW[0] <= address < SRAM_WINDOW[1], address

    def _write_expression(self, path, literal):
        """Apply one write through GDB; the caller decides about verification."""
        try:
            gdb.execute(f"set variable {path} = {literal}", to_string=True)
        except gdb.error as cause:
            self._fail("write", "command", "none", "command_failed",
                       f"write failed for {path}", cause=cause, path=path, value=literal)

    def set_value(self, expression, value):
        """Alias of `write` kept for the 0.2.x name (removal planned in 0.4.0)."""
        self.write(expression, value)

    def breakpoint(self, location, temporary=False, *, condition=None, ignore_count=0, when=None):
        """Set a point and return it (ТЗ API 4.4).

        A repeated request with the same parameters reuses the active persistent point; a temporary
        point or different parameters always create a new one, so a condition is never dropped.
        `when` is the 0.1/0.2 name of `condition`.
        """
        if type(location) is not str or not location.strip():
            self._fail("breakpoint", "validation", "none", "invalid_location",
                       "location must be a non-empty string", location=location)
        condition = self._condition("breakpoint", condition, when)
        if not temporary:
            for point in self.owned:
                if (point.location == location and point.active and not point.temporary
                        and not point.watch and point.condition == condition
                        and point.ignore_count == ignore_count):
                    return point
        if sum(point.active for point in self.owned) >= self.profile["breakpoint_limit"]:
            self._fail("breakpoint", "command", "none", "limit_exceeded",
                       "profile hardware breakpoint budget exhausted",
                       limit=self.profile["breakpoint_limit"])
        try:
            native = gdb.Breakpoint(location, type=gdb.BP_HARDWARE_BREAKPOINT, temporary=temporary)
        except gdb.error as cause:
            self._fail("breakpoint", "command", "none", "command_failed",
                       f"breakpoint failed for {location}", cause=cause, location=location)
        point = Point(native, location, self, temporary=temporary, condition=condition,
                      ignore_count=ignore_count)
        self.owned.append(point)
        try:
            if native.pending:
                self._fail("breakpoint", "command", "none", "symbol_absent",
                           f"symbol is absent from the ELF: {location}", location=location)
            if condition is not None:
                native.condition = condition
            if ignore_count:
                native.ignore_count = ignore_count
        except BaseException:
            point.remove()
            raise
        return point


    def watch(self, path):
        """Watch a writable object for changes (ТЗ API 4.6).

        Only addressable objects inside the mapped image are accepted. A backend without hardware
        watchpoints fails here, and the failure names the operation instead of leaving the scenario
        without stops. The returned point is a regular Point with `with` support.
        """
        if type(path) is not str or not path.strip():
            self._fail("watch", "validation", "none", "invalid_path",
                       "a non-empty object path is required", path=path)
        try:
            value = gdb.parse_and_eval(path)
        except gdb.error as cause:
            self._fail("watch", "validation", "none", "invalid_path",
                       f"{path} is not a valid object path", cause=cause, path=path)
        kind = values.unqualified_type(value.type)
        size = getattr(kind, "sizeof", None)
        address = getattr(value, "address", None)
        if address is None:
            self._fail("watch", "validation", "none", "not_addressable",
                       f"{path} has no address", path=path)
        reason = values.non_watchable(kind) if kind is not None else "unknown"
        if kind is None or reason is not None:
            self._fail("watch", "validation", "none", "unsupported_object",
                       f"{path} is not a watchable object", path=path, kind=reason)
        if type(size) is not int or size not in (1, 2, 4, 8):
            self._fail("watch", "validation", "none", "unsupported_width",
                       f"{path} has an unsupported width", path=path, size=size)
        location = "*" + hex(int(address))
        if int(address) % size:
            self._fail("watch", "validation", "none", "unsupported_width",
                       f"{path} is not naturally aligned", path=path, address=location)
        if sum(point.active for point in self.owned) >= self.profile["breakpoint_limit"]:
            self._fail("watch", "validation", "none", "limit_exceeded",
                       "the watchpoint budget is exhausted", path=path,
                       limit=self.profile["breakpoint_limit"])
        try:
            native = gdb.Breakpoint(location, gdb.BP_WATCHPOINT, gdb.WP_WRITE)
        except (gdb.error, RuntimeError) as cause:
            self._fail("watch", "command", "none", "command_failed",
                       "this backend cannot watch memory", cause=cause, path=path,
                       address=location)
        point = Point(native, path, self)
        point.watch = True
        point.watched = path
        point.snapshot = self._watch_value(path)
        self.owned.append(point)
        return point

    def _watch_value(self, path):
        """Current plain value of a watched object, or None when it cannot be read."""
        try:
            value = gdb.parse_and_eval(path)
            value.fetch_lazy()
            return values.value_to_plain(value, path, gdb)
        except conversion_errors(gdb):
            return None

    def _condition(self, operation, condition, when):
        """Single condition from the 0.3.0 `condition` and the 0.1/0.2 `when` (ТЗ API 4.4.1)."""
        if when is not None and condition is not None and when != condition:
            self._fail(operation, "validation", "none", "conflicting_condition",
                       "condition and when differ", condition=condition, when=when)
        return condition if condition is not None else when

    def reach(self, location, condition=None, *, when=None):
        """Run to a location and return the stop result; the point is temporary (ТЗ API 4.5).

        The point is always created by this call and only that point is removed afterwards; a point
        the scenario set at the same location stays. `when` is the 0.1/0.2 name of `condition`.
        """
        condition = self._condition("reach", condition, when)
        point = self.breakpoint(location, temporary=True, condition=condition)
        # Resolve the addresses while the point exists: a temporary point is gone after the stop.
        addresses = list(point.addresses)
        self.stops.clear()
        try:
            stop = self._advance("reach")
        finally:
            point.remove()
        if not addresses and stop.get("pc") is not None:
            addresses = [stop["pc"]]
        self.report.setdefault("stops", []).append(stop)
        self.check(f"breakpoint reached: {location}", point.number in stop.get("breakpoints", []), True)
        frame = gdb.newest_frame().name()
        stop["frame"] = frame
        self.check(f"frame: {location}", function_name(frame), function_name(location))
        if condition is not None:
            # Never accept a stop that happened after a condition evaluation error.
            self.check(f"condition: {condition}", bool(self.value(condition)), True)
        return dict(operation="reach", outcome="reached", location=location, point=point.number,
                    addresses=addresses, stop=stop)

    def resume(self):
        """Continue execution and return the stop result (ТЗ API 4.5)."""
        self.stops.clear()
        stop = self._advance("resume")
        self.report.setdefault("stops", []).append(stop)
        return dict(operation="resume", outcome="stopped", stop=stop)

    def step(self, count=1, *, unit="source", mode="into"):
        """Step `count` times by source line or instruction (ТЗ API 4.5)."""
        if type(count) is not int or count < 1:
            self._fail("step", "validation", "none", "invalid_count",
                       "count must be a positive integer", count=count)
        commands = {("source", "into"): "step", ("source", "over"): "next",
                    ("instruction", "into"): "stepi", ("instruction", "over"): "nexti"}
        if (unit, mode) not in commands:
            self._fail("step", "validation", "none", "invalid_mode",
                       f"unsupported step mode {unit}/{mode}", unit=unit, mode=mode)
        completed, outcome, stop = 0, "completed", {}
        for _ in range(count):
            stop = self._advance("step", commands[(unit, mode)])
            if stop.get("kind") in ("breakpoint", "watchpoint"):
                outcome = "interrupted"
                break
            if stop.get("kind") != "step":
                self._fail("step", "observe", "completed", "completion_unconfirmed",
                           "step did not stop at a step event", stop=stop, completed=completed,
                           unit=unit, mode=mode)
            completed += 1
        if stop:
            self.report.setdefault("stops", []).append(stop)
        return dict(operation="step", outcome=outcome, requested=count, completed=completed,
                    unit=unit, mode=mode, stop=stop)

    def until(self, location=None):
        """Run to a location in the current frame, or leave the current line (ТЗ API 4.5)."""
        if location is not None and (type(location) is not str or not location.strip()):
            self._fail("until", "validation", "none", "invalid_location",
                       "location must be a non-empty string", location=location)
        command = "until" if location is None else "until " + location
        before = self._frame_identity()
        targets = self._line_addresses(location) if location is not None else []
        stop = self._advance("until", command, targets=targets)
        self.report.setdefault("stops", []).append(stop)
        if location is None:
            outcome = "completed"
        elif stop.get("pc") in targets or (not targets and stop.get("kind") == "location"):
            outcome = "reached"
        elif before is not None and stop.get("function") != before[0]:
            # GDB stops `until` when the current frame returns, before the target is reached; GDB 16
            # calls that `location-reached` too, so only the address proves the target.
            outcome = "frame_exited"
        else:
            outcome = "completed"
        return dict(operation="until", outcome=outcome, location=location, targets=targets, stop=stop)

    def _line_addresses(self, location):
        """Addresses a location resolves to, or an empty list when GDB cannot tell (ТЗ API 4.5)."""
        decode = getattr(gdb, "decode_line", None)
        if not callable(decode):
            return []
        try:
            _rest, sals = decode(location)
        except (gdb.error, RuntimeError, TypeError, ValueError):
            return []
        addresses = []
        for sal in sals or ():
            pc = getattr(sal, "pc", None)
            if pc:
                addresses.append(int(pc))
        return addresses

    def finish(self):
        """Run the rest of the current function and report the returned value (ТЗ API 4.5).

        GDB stores the value of a finished function in its value history ("Value returned is $N"),
        which every supported GDB has; `gdb.Frame` carries no return value. A void function is told
        apart by the declared type, so `None` never stands for both.
        """
        origin = gdb.newest_frame()
        returned_from = function_name(origin.name()) if origin is not None else None
        kind = self._return_type(origin) if origin is not None else None
        history = self._history_count()
        stop = self._advance("finish", "finish")
        self.report.setdefault("stops", []).append(stop)
        frame = gdb.newest_frame()
        value, state = self._finish_value(kind, history)
        return dict(operation="finish", outcome="completed", stop=stop, returned_from=returned_from,
                    function=function_name(frame.name()) if frame is not None else None,
                    return_value=value, return_state=state)

    def _history_count(self):
        """Length of the GDB value history, or None when this GDB cannot report it."""
        count = getattr(gdb, "history_count", None)
        if not callable(count):
            return None
        try:
            return int(count())
        except (gdb.error, RuntimeError, TypeError, ValueError):
            return None

    def _finish_value(self, kind, history_before):
        """Returned value and its state after `finish`: available, void or unavailable."""
        _name, _signed, width = values.return_type_shape(kind)
        if kind is not None and not width and values.type_code_of(kind) == values.type_constant("TYPE_CODE_VOID"):
            return None, "void"
        after = self._history_count()
        if history_before is None or after is None or after <= history_before:
            return None, "unavailable"
        try:
            value = gdb.history(0)
            if getattr(value, "is_optimized_out", False):
                return None, "unavailable"
            value.fetch_lazy()
            return values.value_to_plain(value, "finish", gdb), "available"
        except conversion_errors(gdb) + (RuntimeError, AttributeError):
            return None, "unavailable"

    def _advance(self, operation, command="continue", targets=()):
        """Run one debugger command and describe the stop it produced.

        The stop reason comes from the event queue because a temporary point may already be invalid
        when the command returns. Some GDB versions report no native reason for `finish`; in that case
        a changed frame is what proves the function returned.
        """
        before = self._frame_identity()
        self.stops.clear()
        try:
            gdb.execute(command, to_string=True)
        except gdb.error as cause:
            self._fail(operation, "command", "unknown", "execution_failed",
                       f"{command} failed", cause=cause, command=command)
        stop = dict(self.stops[-1]) if self.stops else {"reason": "unknown", "breakpoints": [],
                                                        "signal": None}
        stop["kind"] = self._stop_kind(stop)
        frame = gdb.newest_frame()
        if frame is not None:
            stop["pc"] = int(frame.pc())
            stop["function"] = function_name(frame.name())
        # GDB 14 attaches no `details` to a stop event, so the native reason is missing for step, until
        # and finish (GDB 15+ report it). The fallback is chosen per command and is never presented as
        # native: the stop carries `inferred` and the report a one-time warning (ТЗ API 4.5).
        moved = before is not None and stop.get("pc") is not None and stop.get("pc") != before[1]
        if stop["kind"] == "unknown" and before is not None:
            if operation == "finish" and stop.get("function") != before[0]:
                stop["kind"] = "function_return"
            elif operation == "step" and moved:
                stop["kind"] = "step"
            elif operation == "until" and moved:
                # GDB 15+ call leaving the line `end-stepping-range` even when it returns into the
                # caller (five-stand matrix), so only a reached target address is a location.
                stop["kind"] = "location" if stop.get("pc") in targets else "step"
            if stop["kind"] != "unknown":
                self._infer(stop, operation)
        if stop["kind"] == "unknown" and operation in ("resume", "reach"):
            # Some backends do not report the watch point stop at all, so the changed object is the
            # evidence: a write watch point can only be seen through the value it protects.
            fired = [point for point in self.owned
                     if point.active and point.watch and point.snapshot is not None
                     and self._watch_value(point.watched) != point.snapshot]
            if fired:
                stop["kind"] = "watchpoint"
                stop["watch"] = [point.id for point in fired]
                self._infer(stop, operation)
        stop.setdefault("evidence", "native" if stop["kind"] != "unknown" else "none")
        if stop["kind"] == "fault":
            self._fail(operation, "observe", "completed", "fault_stop",
                       "stopped at a fault guard", stop=stop)
        if stop["kind"] == "signal":
            self._fail(operation, "observe", "completed", "signal_stop",
                       "stopped by a signal", stop=stop)
        if stop["kind"] == "unknown":
            self._fail(operation, "observe", "completed", "unknown_stop",
                       "stop reason is unknown", stop=stop)
        return stop

    def _infer(self, stop, operation):
        """Mark a stop as inferred and warn once per run that this GDB gives no native reason."""
        stop["inferred"] = True
        stop["evidence"] = "inferred"
        if not getattr(self, "_inference_warned", False):
            self._inference_warned = True
            # report["warnings"] is a list of strings printed by the runner (as the identity warnings).
            self.report.setdefault("warnings", []).append(
                f"inferred_stop: GDB {getattr(gdb, 'VERSION', 'unknown')} reported no stop reason for "
                f"{operation}; the kind is inferred from the frame, the program counter or a watched object")

    def _frame_identity(self):
        """Name and program counter of the current frame, or None when unavailable."""
        frame = gdb.newest_frame()
        if frame is None:
            return None
        try:
            return (function_name(frame.name()), int(frame.pc()))
        except gdb.error:
            return None

    def _stop_kind(self, stop):
        """Classify one stop event into the vocabulary used by the navigation results.

        A stop is a point only when the reported numbers belong to this Target; an unknown number
        (a foreign point, or a temporary point that expired) is reported as an unknown reason.
        """
        numbers = set(stop.get("breakpoints", ()))
        owned = {point.id: point for point in self.owned}
        guards = {point.id for point in self.owned
                  if point.location in self.profile["fault_handlers"]}
        if numbers & guards:
            return "fault"
        if numbers & set(owned):
            # J-Link reports a watch point as an ordinary breakpoint event without a reason, so the
            # kind of the reported point decides; the native reason is only a corroborating hint.
            reported = [owned[number] for number in numbers if number in owned]
            if any(point.watch for point in reported):
                return "watchpoint"
            return "watchpoint" if str(stop.get("native_reason") or "").startswith("watch") \
                else "breakpoint"
        if numbers:
            return "unknown"
        if stop.get("signal") is not None:
            return "signal"
        native = stop.get("native_reason")
        if native == "end-stepping-range":
            return "step"
        if native == "location-reached":
            return "location"
        if native == "function-finished":
            return "function_return"
        if native is not None:
            # The target stopped for a reason we do not classify, but the stop itself is usable.
            return "other"
        return "unknown"

    def boot(self, reset_command):
        self.clear()
        gdb.execute(reset_command)
        for name in self.profile["fault_handlers"]:
            self.breakpoint(name)
        self.reach("main")

    def ret(self, value=None):
        """Return early from the current function, substituting a typed value (ТЗ API 4.7).

        The value is encoded by the declared return type of the frame: the width and signedness come
        from the type, and a value outside the declared range is refused before anything is executed.
        """
        frame = gdb.newest_frame()
        if frame is None or not frame.is_valid():
            self._fail("ret", "validation", "none", "no_frame",
                       "a valid current frame is required", value=value)
        function = function_name(frame.name())
        caller = frame.older()
        caller_name = function_name(caller.name()) if caller is not None else None
        kind = self._return_type(frame)
        if value is None:
            command, applied, type_name = "return", None, None
        elif type(value) is str:
            # A GDB expression is passed through unchanged, as the 0.2.x `force_return` did.
            command, applied, type_name = "return " + value, None, None
        else:
            type_name, signed, width = values.return_type_shape(kind)
            if width == 0:
                self._fail("ret", "validation", "none", "unsupported_type",
                           f"unsupported return type for {function}", type_name=type_name,
                           function=function)
            if type(value) is not int or isinstance(value, bool):
                self._fail("ret", "validation", "none", "unsupported_type",
                           "the returned value must be an integer", value=value,
                           function=function)
            low, high = (-(1 << (width - 1)), (1 << (width - 1)) - 1) if signed \
                else (0, (1 << width) - 1)
            if values.type_code_of(kind) == values.type_constant("TYPE_CODE_BOOL"):
                # A boolean return carries a logical value, not the whole byte.
                high = 1
            if not low <= value <= high:
                self._fail("ret", "validation", "none", "out_of_range",
                           "value outside the declared return width", value=value,
                           low=low, high=high, width=width, function=function)
            applied = value
            literal = hex(value) if value >= 0 else "-" + hex(-value)
            command = f"return ({type_name}){literal}"
        try:
            output = gdb.execute(command, to_string=True)
        except gdb.error as cause:
            self._fail("ret", "command", "unknown", "command_failed",
                       f"{command} failed", cause=cause, command=command, function=function)
        result = dict(operation="ret", function=function, caller=caller_name, supplied=value,
                      outcome="forced", command=command, applied=applied, type_name=type_name,
                      output=output or "")
        self.report.setdefault("mutations", []).append(
            dict(operation="ret", function=function, value=value, command=command))
        return result

    def _return_type(self, frame):
        """Declared return type of a frame.

        `Frame.return_type()` exists only in newer GDB builds, so the function symbol is the fallback:
        its type target is the declared return type.
        """
        reader = getattr(frame, "return_type", None)
        if callable(reader):
            try:
                kind = reader()
            except gdb.error:
                kind = None
            if kind is not None:
                return kind
        name = function_name(frame.name())
        if not name:
            return None
        try:
            symbol = gdb.parse_and_eval(name)
        except gdb.error:
            return None
        kind = getattr(symbol, "type", None)
        if kind is None:
            return None
        target = getattr(kind, "target", None)
        if callable(target):
            try:
                return target()
            except gdb.error:
                return None
        return None

    def reset(self):
        """Reset the target, leave it halted and invalidate the debugger caches (ТЗ API 4.10).

        The command comes from `api.toml` when configured, otherwise from the prepared backend, and a
        session override wins over both. Active points are refused because a reset makes their state
        meaningless; the invalidation runs after any attempt, including a failed one.
        """
        guards = set(self.profile["fault_handlers"])
        active = [point.id for point in self.owned if point.active and point.location not in guards]
        if active:
            self._fail("reset", "validation", "none", "active_points",
                       "active points must be removed before a reset", points=active)
        command = self._reset_command()
        invalidation = []
        try:
            gdb.execute(command, to_string=True)
        except gdb.error as cause:
            self._invalidate(invalidation)
            self._fail("reset", "command", "unknown", "command_failed",
                       "the reset command failed", cause=cause, command=command,
                       invalidation=invalidation)
        self._invalidate(invalidation)
        frame = gdb.newest_frame()
        registers = {"pc": int(frame.pc()) if frame is not None and frame.is_valid() else None}
        entry = dict(operation="reset", outcome="halted", command=command, registers=registers,
                     invalidation=invalidation)
        self.report.setdefault("resets", []).append(entry)
        return dict(entry)

    def _reset_command(self):
        """Reset command in the documented precedence: session, `api.toml`, backend default."""
        override = os.environ.get("STM32_GDBTEST_RESET_COMMAND")
        if override:
            return override
        try:
            configured = self._config["api"]["reset"]["command"]
        except (KeyError, TypeError):
            configured = None
        if configured is not None:
            if type(configured) is not str or not configured.strip():
                self._fail("reset", "validation", "none", "invalid_command",
                           "reset.command must be a non-empty string", command=configured)
            return configured
        return getattr(self.profile, "get", lambda *_: None)("reset_halt") or RESET_COMMAND

    def _invalidate(self, steps):
        """Flush the register cache and the cached frames, recording both outcomes."""
        for name, action in (("flush_register_cache",
                              lambda: gdb.execute("maintenance flush register-cache", to_string=True)),
                             ("invalidate_cached_frames", gdb.invalidate_cached_frames)):
            try:
                action()
            except (gdb.error, AttributeError, RuntimeError) as error:
                steps.append(dict(step=name, status="failed", detail=str(error)))
            else:
                steps.append(dict(step=name, status="done"))

    def execute(self, command):
        """Run a debugger command and return its text output (ТЗ API 4.9).

        The journal keeps the command, the stage, the result, the output length and the truncation
        flag; on truncation it also keeps the SHA-256 of the full output. A debugger error is
        propagated as a failure and the command is never repeated.
        """
        if type(command) is not str or not command.strip():
            self._fail("execute", "validation", "none", "invalid_command",
                       "command must be a non-empty string", command=command)
        if any(character in command for character in ("\r", "\n")):
            self._fail("execute", "validation", "none", "invalid_command",
                       "the command must be a single line", command=command)
        try:
            text = gdb.execute(command, to_string=True)
        except gdb.error as cause:
            self.report.setdefault("executions", []).append(
                dict(operation="execute", command=command, stage="dispatch", result="failed",
                     output_length=0, truncated=False))
            self._fail("execute", "command", "unknown", "command_failed",
                       "the debugger command failed", cause=cause, command=command)
        if type(text) is not str:
            self._fail("execute", "observe", "completed", "invalid_result",
                       "the debugger returned a non-string result", command=command)
        limit = self._execute_limit()
        truncated = len(text) > limit
        entry = dict(operation="execute", command=command, stage="capture", result="ok",
                     output_length=len(text), truncated=truncated, limit=limit)
        if truncated:
            entry["output_sha256"] = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self.report.setdefault("executions", []).append(entry)
        return text

    def _execute_limit(self):
        """Configured output limit of `execute`, falling back to the agreed default."""
        try:
            limit = self._config["api"]["execute"]["output_limit_chars"]
        except (KeyError, TypeError):
            return EXECUTE_OUTPUT_LIMIT
        if type(limit) is not int or limit < 1:
            self._fail("execute", "validation", "none", "invalid_limit",
                       "output_limit_chars must be a positive integer", limit=limit)
        return limit

    def call(self, function, *args):
        """Call a function of the debugged program on the halted core (ТЗ API 4.8).

        Arguments are passed by value; the function runs, so its side effects are kept and the halt
        state is whatever the call produced. The scenario timeout is the only bound on the call.
        """
        if type(function) is not str or not _FUNCTION_NAME.fullmatch(function):
            self._fail("call", "validation", "none", "invalid_function",
                       "a plain function name is required", function=function)
        literals = []
        for argument in args:
            literal = values.argument_literal(argument)
            if literal is None:
                self._fail("call", "validation", "none", "unsupported_argument",
                           "arguments must be finite numbers", function=function,
                           arguments=list(args))
            literals.append(literal)
        expression = f"{function}({', '.join(literals)})"
        kind = self._function_return_type(function)
        try:
            value = gdb.parse_and_eval(expression)
        except gdb.error as cause:
            self._fail("call", "command", "unknown", "command_failed",
                       f"{expression} failed", cause=cause, function=function,
                       arguments=list(args))
        if getattr(value, "is_optimized_out", False):
            self._fail("call", "observe", "completed", "optimized_out",
                       f"the result of {function} is optimized out", function=function)
        _type_name, _signed, width = values.return_type_shape(kind)
        if not width:
            # A void call has no result to convert; the call itself still happened.
            result = dict(operation="call", function=function, arguments=list(args),
                          expression=expression, outcome="returned", return_value=None,
                          return_state="void")
            self.report.setdefault("mutations", []).append(
                dict(operation="call", function=function, expression=expression, value=None))
            return result
        try:
            value.fetch_lazy()
            plain = values.value_to_plain(value, expression, gdb)
        except conversion_errors(gdb) as cause:
            self._fail("call", "observe", "completed", "conversion_failed",
                       f"the result of {function} is unavailable", cause=cause, function=function)
        state = "available"
        result = dict(operation="call", function=function, arguments=list(args),
                      expression=expression, outcome="returned", return_value=plain,
                      return_state=state)
        self.report.setdefault("mutations", []).append(
            dict(operation="call", function=function, expression=expression, value=plain))
        return result

    def _function_return_type(self, function):
        """Declared return type of a named function, or None when the symbol is unknown."""
        try:
            symbol = gdb.parse_and_eval(function)
        except gdb.error:
            return None
        kind = getattr(symbol, "type", None)
        target = getattr(kind, "target", None)
        if callable(target):
            try:
                return target()
            except gdb.error:
                return None
        return None

    def force_return(self, expression):
        """Alias of `ret` kept for the 0.2.x name (removal planned in 0.4.0)."""
        return self.ret(expression)

    def clear(self):
        # remove() rewrites self.owned, so iterate over a snapshot (ТЗ API 4.8).
        for point in list(self.owned):
            point.remove()
        self.owned.clear()

    def close(self):
        gdb.events.stop.disconnect(self.on_stop)
        self.clear()
