"""Target API. Imported only inside GDB's main Python thread."""

import re

import gdb
from stm32_gdbtest.errors import ApiError, CheckFailed, fail  # noqa: F401
from stm32_gdbtest.records import Journal
from stm32_gdbtest.configuration import DEFAULTS, freeze
from stm32_gdbtest import values

_CLONE = re.compile(r"\s*\[clone [^\]]*\]")


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


class Target:
    def __init__(self, report, profile, configuration=None):
        self.report = report
        self.profile = profile
        self._config = configuration.config if configuration else freeze(dict(
            target=profile, api=dict(schema=1, records=dict(DEFAULTS)), image=None))
        self._config_props = configuration.config_props if configuration else freeze(
            dict(target=None, api=None, image=None))
        limits = self._config['api']['records']
        self._journal = Journal(**{key: limits[key] for key in DEFAULTS})
        self.owned = []
        self.stops = []
        gdb.events.stop.connect(self.on_stop)

    @property
    def config(self):
        return self._config

    @property
    def config_props(self):
        return self._config_props

    def record(self, name, data):
        return self._journal.record(name, data)

    def records(self, name=None):
        return self._journal.records(name)

    def on_stop(self, event):
        # Capture primitive values now: temporary breakpoint objects expire after stop.
        self.stops.append({"type": type(event).__name__,
                           "breakpoints": [bp.number for bp in getattr(event, "breakpoints", ())],
                           "signal": getattr(event, "stop_signal", None)})

    def check(self, name, actual, expected):
        """Record one comparison and fail the scenario on a mismatch (ТЗ API 4.1)."""
        passed = actual == expected
        self.report["checks"].append(dict(name=name, actual=actual, expected=expected, passed=passed))
        print(f"{'PASS' if passed else 'FAIL'} {name}: {actual!r}, expected {expected!r}")
        if not passed:
            raise CheckFailed(name, actual=actual, expected=expected)

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
        except gdb.error as cause:
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
        before = self._read_value(path, path)
        self._write_expression(path, value)
        after = self._read_value(path, path) if verify else None
        self.report.setdefault("mutations", []).append(
            dict(expression=path, value=value, before=before, after=after))
        if verify and after != value:
            values.verification_failed(path, value, after)
        return dict(operation="write", path=path, value=value, before=before, after=after,
                    verified=bool(verify))

    def _write_expression(self, path, value):
        """Apply one write through GDB; the caller decides about verification."""
        try:
            gdb.execute(f"set variable {path} = {value!r}", to_string=True)
        except gdb.error as cause:
            self._fail("write", "command", "none", "command_failed",
                       f"write failed for {path}", cause=cause, path=path, value=value)

    def set_value(self, expression, value):
        """Alias of `write` kept for the 0.2.x name (removal planned in 0.4.0)."""
        self.write(expression, value)

    def breakpoint(self, function, temporary=False, when=None):
        if sum(bp.is_valid() for bp in self.owned) >= self.profile["breakpoint_limit"]:
            raise RuntimeError("Profile hardware breakpoint budget exhausted")
        bp = gdb.Breakpoint(function, type=gdb.BP_HARDWARE_BREAKPOINT, temporary=temporary)
        self.owned.append(bp)
        try:
            if bp.pending:
                raise RuntimeError(f"Breakpoint symbol is absent from ELF: {function}")
            if when is not None:
                bp.condition = when
        except BaseException:
            bp.delete()
            raise
        return bp

    def reach(self, function, when=None):
        bp = self.breakpoint(function, temporary=True, when=when)
        number = bp.number
        self.stops.clear()
        try:
            gdb.execute("continue")
            stop = self.stops[-1] if self.stops else {}
            self.report.setdefault("stops", []).append(stop)
            self.check(f"breakpoint reached: {function}", number in stop.get("breakpoints", []), True)
            frame = gdb.newest_frame().name()
            stop["frame"] = frame
            self.check(f"frame: {function}", function_name(frame), function_name(function))
            if when is not None:
                # GDB can stop after a condition evaluation error; never accept that silently.
                self.check(f"condition: {when}", bool(self.value(when)), True)
        finally:
            if bp.is_valid():
                bp.delete()

    def boot(self, reset_command):
        self.clear()
        gdb.execute(reset_command)
        for name in self.profile["fault_handlers"]:
            self.breakpoint(name)
        self.reach("main")

    def force_return(self, expression):
        function = gdb.newest_frame().name()
        gdb.execute("return " + expression)
        self.report.setdefault("mutations", []).append(
            dict(operation="force_return", function=function, value=expression))

    def clear(self):
        for bp in self.owned:
            if bp.is_valid():
                bp.delete()
        self.owned.clear()

    def close(self):
        gdb.events.stop.disconnect(self.on_stop)
        self.clear()
