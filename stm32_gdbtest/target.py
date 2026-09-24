"""Target API. Imported only inside GDB's main Python thread."""

import gdb


class CheckFailed(AssertionError):
    pass


class Target:
    def __init__(self, report, profile):
        self.report = report
        self.profile = profile
        self.owned = []
        self.stops = []
        gdb.events.stop.connect(self.on_stop)

    def on_stop(self, event):
        # Capture primitive values now: temporary breakpoint objects expire after stop.
        self.stops.append({"type": type(event).__name__,
                           "breakpoints": [bp.number for bp in getattr(event, "breakpoints", ())],
                           "signal": getattr(event, "stop_signal", None)})

    def check(self, name, actual, expected):
        passed = actual == expected
        self.report["checks"].append(dict(name=name, actual=actual, expected=expected, passed=passed))
        print(f"{'PASS' if passed else 'FAIL'} {name}: {actual!r}, expected {expected!r}")
        if not passed:
            raise CheckFailed(name)

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

    def set_value(self, expression, value):
        """Explicit, logged mutation; test authors must check HAL preconditions first."""
        before = self.value(expression)
        gdb.execute(f"set variable {expression} = {value}")
        after = self.value(expression)
        self.report.setdefault("mutations", []).append(
            dict(expression=expression, value=value, before=before, after=after))

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
            self.check(f"frame: {function}", gdb.newest_frame().name(), function)
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
