"""Явные C++-вызовы и отказы до исполнения, без периферии."""
from stm32_gdbtest import case, Pointer, Reference


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


@case('HW_CPP_OBJECT_SYNC', timeout_s=20, labels=('emulator',))
def cpp_object_sync(t):
    t.reach('ready')
    saved = t.read('probe.value')
    try:
        t.call('Probe::add', 4, this='&probe', timeout=2)
        result = t.call('Probe::read', this='probe_ptr', signature='unsigned int() const', timeout=2)
        t.check('method reads changed state', result['return_value'], 7)
        t.check('object address audited', result['this_address'], t.read('&probe'))
        result = t.call('demo::overloaded', -2, signature='unsigned int(int)', timeout=2)
        t.check('signed overload', result['return_value'], 4294967294)
        t.check('one execution per call', t.read('calls'), 3)
    finally:
        t.write('probe.value', saved)
        t.check('object restored', t.read('probe.value'), saved)


@case('HW_CPP_OBJECT_ASYNC', timeout_s=30, labels=('emulator',))
async def cpp_object_async(t):
    await t.reach('ready')
    saved = t.read('probe.value')
    try:
        await t.call('Probe::add', 4, this='probe_ptr', timeout=2)
        result = await t.call('Probe::choose', 2, this='&probe', signature='unsigned int(int)', timeout=2)
        t.check('mutable overload', result['return_value'], 9)
        result = await t.call('Probe::choose', 2, this='const_probe', signature='unsigned int(unsigned int) const', timeout=2)
        t.check('const overload', result['return_value'], 109)
        result = await t.call('Probe::inspect', this='volatile_probe', signature='unsigned int() volatile', timeout=2)
        t.check('volatile method', result['return_value'], 7)
        result = await t.call('Probe::inspect_cv', this='cv_probe', signature='unsigned int() const volatile', timeout=2)
        t.check('const volatile method', result['return_value'], 7)
        # Ошибки не должны менять объект или счётчик вызовов.
        for name, args, obj, sig, error in (
            ('Probe::inspect', (), 'cv_probe', None, 'this_qualifiers'),
            ('Probe::add', (1,), 'const_probe', None, 'this_qualifiers'),
            ('Probe::add', (1,), 'volatile_probe', None, 'this_qualifiers'),
            ('Probe::add', (1,), 'null_probe', None, 'invalid_this'),
            ('Probe::add', (1,), '&other', None, 'this_type_mismatch'),
            ('Probe::add', (1,), 'probe_ptr()', None, 'invalid_this'),
            ('Probe::add', (1,), '(Probe*)0x40000000', None, 'invalid_this'),
            ('Probe::choose', (1,), '&probe', None, 'ambiguous_function'),
            ('Probe::read', (), '&probe', 'unsigned int()', 'signature_mismatch'),
            ('Probe::read', (), '&probe', 'int(*)()', 'invalid_signature'),
            ('Probe::twice', (1,), '&probe', None, 'unexpected_this'),
            ('VirtualProbe::run', (), '&probe', None, 'unsupported_method'),
            ('Probe::Probe', (), '&probe', None, 'unsupported_method'),
        ):
            with t.refused(error):
                await t.call(name, *args, this=obj, signature=sig, timeout=2)
            t.check('no execution after ' + error, t.read('calls'), 5)
            t.check('object unchanged after ' + error, t.read('probe.value'), 7)
    finally:
        t.write('probe.value', saved)
        t.check('object restored', t.read('probe.value'), saved)


@case('HW_CPP_OBJECT_BREAK', timeout_s=20, labels=('emulator',))
async def cpp_object_break(t):
    await t.reach('ready')
    t.breakpoint('Probe::add')
    # Остановка внутри вызова не должна считаться завершённым возвратом.
    await t.call('Probe::add', 1, this='&probe', timeout=2)


@case('HW_CPP_ARGUMENTS_SYNC', timeout_s=20, labels=('emulator',))
def cpp_arguments_sync(t):
    t.reach('ready')
    result = t.call('demo::sum', Pointer('samples', count=4), 4,
                    signature='unsigned int(ReadonlyWord *, unsigned int)', timeout=2)
    t.check('array sum', result['return_value'], 10)
    t.check('known array extent', result['argument_bindings'][0]['extent'], 'known')
    result = t.call('c_sum', Pointer('samples_ptr', count=4), 4, timeout=2)
    t.check('C function uses typed resolution', result['return_value'], 10)
    t.check('declared pointer extent', result['argument_bindings'][0]['extent'], 'declared')
    result = t.call('demo::nullable', Pointer.null(), timeout=2)
    t.check('explicit null', result['return_value'], 99)
    t.check('three executions', t.read('calls'), 3)


@case('HW_CPP_ARGUMENTS_ASYNC', timeout_s=30, labels=('emulator',))
async def cpp_arguments_async(t):
    await t.reach('ready')
    saved = [t.read('samples[' + str(i) + ']') for i in range(6)]
    old_scalar, old_probe = t.read('scalar'), t.read('probe.value')
    try:
        await t.call('demo::fill', Pointer('samples_ptr', count=4), 4, timeout=2)
        for i, value in enumerate(saved):
            t.check('buffer and guard ' + str(i), t.read('samples[' + str(i) + ']'), value + (10 if i < 4 else 0))
        await t.call('demo::bump', Reference('scalar'), signature='void(unsigned int &)', timeout=2)
        result = await t.call('demo::peek', Reference('scalar'), signature='unsigned int(const unsigned int &)', timeout=2)
        t.check('reference writes original', result['return_value'], old_scalar + 7)
        await t.call('demo::update', Reference('probe'), timeout=2)
        t.check('object reference', t.read('probe.value'), old_probe + 9)
        for name, args, error in (
            ('demo::fill', (Pointer('samples', count=7), 7), 'argument_range'),
            ('demo::fill', (Pointer('mmio_ptr'), 1), 'argument_range'),
            ('demo::fill', (Pointer('unaligned_ptr'), 1), 'argument_range'),
            ('demo::fill', (Pointer('null_samples'), 1), 'argument_range'),
            ('demo::fill', (Pointer('&scalar', count=2), 2), 'argument_range'),
            ('demo::fill', (Pointer('readonly_samples', count=4), 4), 'argument_qualifiers'),
            ('demo::sum', (Pointer('&probe'), 1), 'argument_type_mismatch'),
            ('demo::bump', (Pointer.null(),), 'argument_type_mismatch'),
            ('demo::bump', (Reference('samples_ptr'),), 'argument_type_mismatch'),
            ('demo::double_pointer', (Pointer('&samples_ptr'),), 'unsupported_argument'),
            ('demo::fill', (0, 1), 'unsupported_argument'),
        ):
            with t.refused(error):
                await t.call(name, *args, timeout=2)
            t.check('no execution after ' + error, t.read('calls'), 4)
    finally:
        for i, value in enumerate(saved):
            t.write('samples[' + str(i) + ']', value)
        t.write('scalar', old_scalar)
        t.write('probe.value', old_probe)
        for i, value in enumerate(saved):
            t.check('buffer restored ' + str(i), t.read('samples[' + str(i) + ']'), value)
        t.check('scalar restored', t.read('scalar'), old_scalar)
        t.check('probe restored', t.read('probe.value'), old_probe)
