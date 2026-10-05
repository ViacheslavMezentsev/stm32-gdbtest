"""Expectations for `Target.check` beyond equality (ТЗ API 4.1.2).

RU: Сопоставители передаются третьим аргументом `check`: `t.check("VDDA", vdda, within(2900, 3600))`.
    В отчёте остаются фактическое значение и границы, а не `True`.
EN: Matchers are passed as the third argument of `check`: `t.check("VDDA", vdda, within(2900, 3600))`.
    The report keeps the actual value and the bounds instead of `True`.
"""

import re

from stm32_gdbtest.errors import fail


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


class Matcher:
    """Base class: `matches(actual)` decides, `expected` is the report form, `kind` names the check."""

    kind = None

    def matches(self, actual):
        raise NotImplementedError

    @property
    def expected(self):
        raise NotImplementedError

    def __repr__(self):
        return f"{type(self).__name__}({self.expected!r})"


class within(Matcher):
    """`low <= actual <= high` for numbers; a non-numeric value does not match."""

    kind = "range"

    def __init__(self, low, high):
        if not (_number(low) and _number(high)) or low > high:
            fail("check", "validation", "none", "invalid_bounds", "bounds must be numbers with low <= high",
                 low=low, high=high)
        self.low, self.high = low, high

    def matches(self, actual):
        return _number(actual) and self.low <= actual <= self.high

    @property
    def expected(self):
        return dict(low=self.low, high=self.high)

    def __str__(self):
        return f"{self.low!r}..{self.high!r}"


class near(Matcher):
    """`|actual - value| <= tolerance` for numbers."""

    kind = "near"

    def __init__(self, value, tolerance):
        if not _number(value) or not _number(tolerance) or tolerance < 0:
            fail("check", "validation", "none", "invalid_tolerance",
                 "value must be a number and tolerance a non-negative number", value=value, tolerance=tolerance)
        self.value, self.tolerance = value, tolerance

    def matches(self, actual):
        return _number(actual) and abs(actual - self.value) <= self.tolerance

    @property
    def expected(self):
        return dict(value=self.value, tolerance=self.tolerance)

    def __str__(self):
        return f"{self.value!r} ± {self.tolerance!r}"


class one_of(Matcher):
    """`actual` equals one of the options."""

    kind = "in"

    def __init__(self, *options):
        if not options:
            fail("check", "validation", "none", "invalid_options", "at least one option is required")
        self.options = list(options)

    def matches(self, actual):
        return actual in self.options

    @property
    def expected(self):
        return {"in": list(self.options)}

    def __str__(self):
        return f"one of {self.options!r}"


class matches(Matcher):
    """A Python regular expression found in a text value (`re.search`); anchor it with `^`/`$`."""

    kind = "matches"

    def __init__(self, pattern):
        if type(pattern) is not str:
            fail("check", "validation", "none", "invalid_pattern", "pattern must be a string", pattern=pattern)
        try:
            self._compiled = re.compile(pattern)
        except re.error as cause:
            fail("check", "validation", "none", "invalid_pattern", f"invalid pattern: {cause}", pattern=pattern)
        self.pattern = pattern

    def matches(self, actual):
        return type(actual) is str and self._compiled.search(actual) is not None

    @property
    def expected(self):
        return {"matches": self.pattern}

    def __str__(self):
        return f"text matching {self.pattern!r}"
