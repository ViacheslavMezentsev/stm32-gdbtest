"""Target API. Imported only inside GDB's main Python thread."""

import re

import gdb
from stm32_gdbtest.records import Journal
from stm32_gdbtest.configuration import DEFAULTS, freeze

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


class CheckFailed(AssertionError):
    pass


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
