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
