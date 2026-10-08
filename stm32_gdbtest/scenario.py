"""Scenario completion shared by GDB execution and host regression tests."""
import sys

from stm32_gdbtest.errors import CheckFailed, fail


class ScenarioSkipped(BaseException):
    """Internal control flow; ordinary except Exception must not swallow a skip."""


def skip(target, reason):
    if type(reason) is not str or not reason.strip():
        fail('skip', 'validation', 'none', 'invalid_arguments', 'skip reason must be a nonempty string')
    limit = target._config['api']['records']['max_text_bytes']
    try:
        size = len(reason.encode('utf-8'))
    except UnicodeEncodeError:
        fail('skip', 'validation', 'none', 'invalid_arguments', 'skip reason must be valid Unicode')
    if size > limit:
        fail('skip', 'validation', 'none', 'limit_exceeded', 'skip reason exceeds text limit', limit=limit)
    # An active exception (including one in finally) must not be replaced with SKIP.
    active = sys.exc_info()[1]
    if active is not None and not isinstance(active, ScenarioSkipped):
        raise active
    reject_failed_checks(target)
    if getattr(target, '_skip_reason', None) is not None:
        fail('skip', 'command', 'none', 'already_skipped', 'scenario caught a previous skip')
    target._skip_reason = reason
    raise ScenarioSkipped(reason)


def reject_failed_checks(target):
    for check in target.report.get('checks', []):
        if check.get('passed') is False:
            raise CheckFailed(check.get('name', 'previous check'), check.get('actual'), check.get('expected'))


def invoke(function, target):
    """Return only on successful completion; keep failures and intercepted skips visible."""
    function(target)
    reject_failed_checks(target)
    if getattr(target, '_skip_reason', None) is not None:
        fail('skip', 'command', 'none', 'intercepted_skip', 'scenario caught skip and returned')
