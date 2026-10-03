"""TECH-010 consumer-side technique; not a public stm32_gdbtest API."""


def check_values(target, checks):
    """Rows: (label, actual C expression, integer or expected C expression).

    Evaluate actual before expected, then check; stop at the first exception.
    This is sequential observation, not an atomic peripheral snapshot.
    """
    for name, expression, expected in checks:
        actual = target.value(expression)
        if isinstance(expected, str):
            expected = target.value(expected)
        target.check(name, actual, expected)
