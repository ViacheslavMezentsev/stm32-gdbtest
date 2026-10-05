"""Operation outcomes and diagnostics of the scenario API (ТЗ API 0.3.0, 6.6-6.7).

RU: Отказы операций отделены от несовпадения проверок: `ApiError` описывает, что делали, на каком
    шаге, с каким наблюдаемым эффектом и почему; `CheckFailed` — только несовпадение проверки.
EN: Operation failures are separated from check mismatches: `ApiError` describes what was attempted,
    at which stage, with which observed effect and why; `CheckFailed` is only a check mismatch.
"""

# Canonical operation names; the aliases of Q4 map onto them.
OPERATIONS = (
    "read", "write", "eval", "registers", "frames", "breakpoint", "watch", "resume", "reach",
    "step", "until", "finish", "ret", "call", "reset", "execute", "record", "records", "config",
    "check", "symbol", "memory", "locals", "arguments", "point"
)

# Where the operation stopped: input validation, the backend command, or observing the result.
STAGES = ("validation", "command", "observe", "readback")

# Observed effect on the target; `unknown` means the attempt may or may not have changed state, and
# `completed` means the operation finished while its result is unusable.
EFFECTS = ("none", "unknown", "partial", "applied", "completed")


class ApiError(Exception):
    """An operation failure with structured diagnostics.

    `details` always carries `operation`, `stage`, `effect` and `code`; extra keyword arguments are
    merged in. The original debugger error stays available as the exception cause.
    """

    def __init__(self, message, **details):
        super().__init__(message)
        self.details = details

    @property
    def code(self):
        return self.details.get("code")

    def __str__(self):
        return str(self.args[0]) if self.args else ""


class CheckFailed(ApiError, AssertionError):
    """A scenario check did not match its expectation (ТЗ API 4.1)."""

    def __init__(self, name, actual=None, expected=None, **details):
        super().__init__(f"check failed: {name}",
                         operation="check", stage="observe", effect="none", code="mismatch",
                         check=name, actual=actual, expected=expected, **details)
        self.name = name


class RecordError(ApiError, ValueError):
    """Invalid evidence or an exceeded journal limit (ТЗ API 4.9; public since 0.2.1)."""

    def __init__(self, code, message, *, limit=None):
        """Keep the public `code`/`limit` attributes and expose both through `details`."""
        super().__init__(message, operation="record", stage="validation", effect="none", code=code)
        self.limit = limit
        self.details["limit"] = limit


def fail(operation, stage, effect, code, message, cause=None, **details):
    """Raise `ApiError` with validated vocabulary, keeping an explicit cause when given.

    The cause is set only when the caller passes one, so an explicit `cause=None` does not expose an
    unrelated exception that happens to be handled by the caller.
    """
    if operation not in OPERATIONS:
        raise ValueError(f"unknown operation: {operation}")
    if stage not in STAGES:
        raise ValueError(f"unknown stage: {stage}")
    if effect not in EFFECTS:
        raise ValueError(f"unknown effect: {effect}")
    if type(code) is not str or not code:
        raise ValueError("code must be a non-empty string")
    error = ApiError(message, operation=operation, stage=stage, effect=effect, code=code, **details)
    if cause is not None:
        error.__cause__ = cause
    raise error
