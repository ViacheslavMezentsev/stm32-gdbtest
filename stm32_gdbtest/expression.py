"""Scoped GDB settings; no claim of side-effect-free expressions (ТЗ API 4.23)."""
from contextlib import contextmanager

from stm32_gdbtest.errors import fail


def setting(value):
    if type(value) is bool:
        return 'on' if value else 'off'
    return 'unlimited' if value is None else str(value)


@contextmanager
def parameters(gdb, requested):
    previous, primary = {}, None
    try:
        # Query every capability before changing anything.
        try:
            previous = {name: gdb.parameter(name) for name in requested}
        except Exception as cause:
            fail('eval', 'validation', 'none', 'unsupported_gdb_parameter',
                 'Required GDB parameter unavailable', cause=cause)
        for name, value in requested.items():
            gdb.execute('set ' + name + ' ' + setting(value), to_string=True)
            if gdb.parameter(name) != value:
                fail('eval', 'validation', 'none', 'parameter_not_applied',
                     'GDB parameter was not applied', parameter=name)
        yield
    except BaseException as cause:
        primary = cause
        raise
    finally:
        errors = []
        for name, value in reversed(list(previous.items())):
            try:
                gdb.execute('set ' + name + ' ' + setting(value), to_string=True)
                if gdb.parameter(name) != value:
                    raise RuntimeError('parameter readback mismatch')
            except Exception as cause:
                errors.append(dict(parameter=name, error=str(cause)))
        if errors:
            gdb._stm32_parameter_cleanup_errors = getattr(gdb, '_stm32_parameter_cleanup_errors', []) + errors
            if primary is not None:
                primary.parameter_cleanup_errors = errors
                if hasattr(primary, 'add_note'):
                    primary.add_note('GDB parameter restoration failed: ' + repr(errors))
            else:
                fail('eval', 'observe', 'unknown', 'parameter_restore_failed',
                     'GDB parameters not restored', errors=errors)


def evaluate(gdb, expression):
    with parameters(gdb, {'may-call-functions': False}):
        try:
            return gdb.parse_and_eval(expression)
        except gdb.error as cause:
            if 'may-call-functions is off' in str(cause):
                fail('eval', 'command', 'unknown', 'expression_call_forbidden',
                     'Use explicit call instead of an inferior call in an expression', cause=cause)
            raise
