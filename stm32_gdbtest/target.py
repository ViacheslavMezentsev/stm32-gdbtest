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


class Point:
    """A set point and its state (ТЗ API 4.4).

    The object owns one native `gdb.Breakpoint`, supports the context manager (`with` removes the
    point on exit) and keeps the number of stops observed for it.
    """

    def __init__(self, native, location, owner=None):
        self._native = native
        # The number is captured now: GDB refuses attribute access on a deleted breakpoint.
        self._number = native.number
        self.location = location
        self.hit_count = 0
        self._owner = owner

    @property
    def id(self):
        return self._number

    number = id

    @property
    def addresses(self):
        """Resolved addresses; a deleted point reports none instead of raising."""
        try:
            return list(self._native.locations)
        except (AttributeError, gdb.error, RuntimeError):
            return []

    @property
    def active(self):
        try:
            return self._native.is_valid() and self._native.enabled
        except RuntimeError:
            return False

    def remove(self):
        """Delete the point and forget it; a repeated removal is not an error."""
        try:
            valid = self._native.is_valid()
        except RuntimeError:
            valid = False
        if valid:
            self._native.delete()
        if self._owner is not None:
            self._owner.owned[:] = [point for point in self._owner.owned if point is not self]

    def __enter__(self):
        return self

    def __exit__(self, kind, value, traceback):
        self.remove()
        return False

    def __repr__(self):
        return f"Point(id={self._native.number}, location={self.location!r}, active={self.active})"


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
        numbers = [bp.number for bp in getattr(event, "breakpoints", ())]
        self.stops.append({"type": type(event).__name__, "breakpoints": numbers,
                           "signal": getattr(event, "stop_signal", None),
                           "native_reason": getattr(event, "details", {}).get("reason")
                           if isinstance(getattr(event, "details", {}), dict) else None})
        for point in self.owned:
            if point.id in numbers:
                point.hit_count += 1

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

    def breakpoint(self, location, *, temporary=False, condition=None, ignore_count=0):
        """Set a point and return it; a repeated target reuses the active point (ТЗ API 4.4)."""
        if type(location) is not str or not location.strip():
            self._fail("breakpoint", "validation", "none", "invalid_location",
                       "location must be a non-empty string", location=location)
        for point in self.owned:
            if point.location == location and point.active:
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
        point = Point(native, location, self)
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

    def reach(self, location, *, condition=None):
        """Run to a location and return the stop result; the point is temporary (ТЗ API 4.5)."""
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
        return dict(operation="step", outcome=outcome, requested=count, completed=completed,
                    unit=unit, mode=mode, stop=stop)

    def until(self, location=None):
        """Run to a location in the current frame, or leave the current line (ТЗ API 4.5)."""
        if location is not None and (type(location) is not str or not location.strip()):
            self._fail("until", "validation", "none", "invalid_location",
                       "location must be a non-empty string", location=location)
        command = "until" if location is None else "until " + location
        stop = self._advance("until", command)
        outcome = "reached" if location is not None and stop.get("kind") == "location" else "completed"
        return dict(operation="until", outcome=outcome, location=location, stop=stop)

    def finish(self):
        """Run the rest of the current function (ТЗ API 4.5)."""
        stop = self._advance("finish", "finish")
        frame = gdb.newest_frame()
        value = getattr(frame, "return_value", None) if frame is not None else None
        available = value is not None and not getattr(value, "is_optimized_out", False)
        if available:
            try:
                value.fetch_lazy()
            except gdb.error:
                available = False
        return dict(operation="finish", outcome="completed", stop=stop,
                    function=function_name(frame.name()) if frame is not None else None,
                    return_value=int(value) if available else None,
                    return_state="available" if available else "unavailable")

    def _advance(self, operation, command="continue"):
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
        if stop["kind"] == "unknown" and before is not None and stop.get("function") != before[0]:
            # `finish` returned into another function while GDB reported no native reason.
            stop["kind"] = "function_return"
        if stop["kind"] == "unknown" and before is not None and stop.get("function") == before[0] \
                and stop.get("pc") != before[1]:
            # Single stepping moved the program counter inside one function without a native reason.
            stop["kind"] = "step"
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

    def force_return(self, expression):
        function = gdb.newest_frame().name()
        gdb.execute("return " + expression)
        self.report.setdefault("mutations", []).append(
            dict(operation="force_return", function=function, value=expression))

    def clear(self):
        for point in self.owned:
            point.remove()
        self.owned.clear()

    def close(self):
        gdb.events.stop.disconnect(self.on_stop)
        self.clear()
