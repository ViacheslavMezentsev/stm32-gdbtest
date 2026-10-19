"""Live-window acceptance on the neutral Renode ELF; no physical hardware."""
from stm32_gdbtest import case


@case('HW_EMU_LIVE', timeout_s=15, labels=('emulator',))
async def live(t):
    t.breakpoint('observe', temporary=True)
    t.resume(sync=False)
    early = await t.wait(timeout=2.0)
    t.check('early breakpoint', early['stop']['kind'], 'breakpoint')
    t.check('repeat halt', (await t.halt(timeout=1.0))['outcome'], 'stopped')
    for n in range(2):
        started = t.resume(sync=False)
        with t.refused('not_stopped'):
            t.read('counter')
        with t.refused('not_stopped'):
            t.write('counter', 7)
        with t.refused('not_stopped'):
            t.resume(sync=False)
        window = await t.wait(timeout=0.05)
        t.check('passive timeout', window['outcome'], 'timeout')
        stopped = await t.halt(timeout=2.0)
        t.check('halt confirmed', stopped['outcome'], 'stopped')
        t.check('current generation', stopped['generation'], started['generation'])
        t.check('memory after halt', t.read('counter'), 3)
    with t.refused('invalid_timeout'):
        await t.wait(timeout=0)
    t.record('live', {'windows': 2})


@case('HW_EMU_LIVE_ERROR', timeout_s=15, labels=('emulator',))
async def live_error(t):
    t.resume(sync=False)
    raise ValueError('intentional error while running')


@case('HW_EMU_LIVE_SKIP', timeout_s=15, labels=('emulator',))
async def live_skip(t):
    t.resume(sync=False)
    t.skip('intentional skip while running')


@case('HW_EMU_LIVE_FAIL', timeout_s=15, labels=('emulator',))
async def live_fail(t):
    t.resume(sync=False)
    t.check('intentional failure while running', False, True)


@case('HW_EMU_LIVE_RETURN', timeout_s=15, labels=('emulator',))
async def live_return(t):
    t.resume(sync=False)
    t.record('return', {'cleanup': 'runner must halt'})


@case('HW_EMU_SYNC_REFUSAL', timeout_s=15, labels=('emulator',))
def sync_refusal(t):
    with t.refused('async_required'):
        t.resume(sync=False)


@case('HW_EMU_LIVE_FAULT', timeout_s=15, labels=('emulator',))
async def live_fault(t):
    # Neutral symbol stands in for a guard; no real CPU fault is claimed.
    t.fault_guards.append('observe')
    t.breakpoint('observe', temporary=True)
    t.resume(sync=False)
    await t.wait(timeout=2.0)


@case('HW_EMU_DISPATCH', timeout_s=20, labels=('emulator',))
async def dispatch(t):
    # Navigation must work both before and after the first coroutine suspension.
    await t.reach('observe')
    await t.wait(timeout=1)
    await t.step(unit='instruction')
    await t.until()
    await t.finish()
    result = await t.call('calculate', 7, timeout=2)
    t.check('call result', result['return_value'], 22)
    with t.refused('unsupported_async_command'):
        t.execute('continue')
    with t.refused('unsupported_backend'):
        await t.reset()
    with t.refused('expression_call_forbidden'):
        t.read('calculate(7)')
    with t.refused('command_failed'):
        await t.call('endless', timeout=1)
    t.check('still readable after timeout', t.read('counter'), 3)
    operation = t.step(unit='instruction')
    await operation
    with t.refused('already_awaited'):
        await operation


@case('HW_EMU_DROPPED', timeout_s=10, labels=('emulator',))
async def dropped(t):
    t.reach('observe')


@case('HW_EMU_CALL_BREAK', timeout_s=10, labels=('emulator',))
async def call_break(t):
    await t.reach('observe')
    t.breakpoint('calculate')
    await t.call('calculate', 7, timeout=2)


@case('HW_EMU_NAV_TIMEOUT', timeout_s=10, labels=('emulator',))
async def nav_timeout(t):
    await t.reach('observe')
    try:
        with t.refused('operation_timeout'):
            await t.resume(timeout=0.05)
    finally:
        await t.halt(timeout=2)
    t.check('read after timeout cleanup', t.read('counter'), 3)


@case('HW_EMU_RET_ASYNC', timeout_s=15, labels=('emulator',))
async def ret_async(t):
    await t.reach('calculate')
    t.ret(8)
    point = t.breakpoint('observe', temporary=True)
    stopped = await t.resume()
    t.check('expected point', point.number in stopped['stop']['breakpoints'], True)
    t.check('forced value consumed', t.read('counter'), 10)


@case('HW_EMU_REACH_TIMEOUT', timeout_s=10, labels=('emulator',))
async def reach_timeout(t):
    await t.reach('observe')
    try:
        with t.refused('operation_timeout'):
            await t.reach('calculate', timeout=0.05)
    finally:
        await t.halt(timeout=2)
    # The temporary point remains owned until it is safe to remove.
    t.clear()


@case('HW_EMU_DROPPED_WAIT', timeout_s=10, labels=('emulator',))
async def dropped_wait(t):
    t.wait(timeout=1)
