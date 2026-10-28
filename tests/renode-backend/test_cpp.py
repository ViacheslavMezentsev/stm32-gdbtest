"""Явные C++-вызовы и отказы до исполнения, без периферии."""
from stm32_gdbtest import case


@case('HW_CPP_SYNC', timeout_s=20, labels=('emulator',))
def cpp_sync(t):
    t.reach('ready')
    result = t.call('demo::increment', 6, timeout=2)
    t.check('namespace', result['return_value'], 7)
    result = t.call('Probe::twice', 6, timeout=2)
    t.check('static', result['return_value'], 12)
    t.check('exactly two calls', t.read('calls'), 2)
    with t.refused('ambiguous_function'):
        t.call('demo::overloaded', 1, timeout=2)
    t.check('no overload executed', t.read('calls'), 2)


@case('HW_CPP_ASYNC', timeout_s=30, labels=('emulator',))
async def cpp_async(t):
    await t.reach('ready')
    request = t.call('demo::increment', 6, timeout=2)
    # Создание awaitable ещё не исполняет код цели.
    result = await request
    t.check('namespace', result['return_value'], 7)
    result = await t.call('Probe::twice', 6, timeout=2)
    t.check('static', result['return_value'], 12)
    result = await t.call('demo::clear', timeout=2)
    t.check('void', result['return_state'], 'void')
    for name, args, error in (
        ('demo::overloaded', (1,), 'ambiguous_function'),
        ('demo::missing', (), 'function_unavailable'),
        ('Probe::absent', (), 'function_unavailable'),
        ('Probe::add', (1,), 'unsupported_method'),
        ('demo::pointer', (0,), 'unsupported_argument'),
        ('demo::floating', (1,), 'unsupported_return'),
        ('demo::increment', (), 'argument_count'),
        ('demo::increment', (-1,), 'argument_range'),
        ('demo::increment', (1.5,), 'unsupported_argument'),
        ('demo::increment', ('free_cpp(7)',), 'unsupported_argument'),
        ('free_cpp', ('free_cpp(7)',), 'unsupported_argument'),
        ('probe.add', (1,), 'invalid_function'),
    ):
        with t.refused(error):
            await t.call(name, *args, timeout=2)
        t.check('refusal did not execute ' + name, t.read('calls'), 3)
    with t.refused('expression_call_forbidden'):
        t.read('demo::increment(7)')
    t.check('guard did not execute', t.read('calls'), 3)
