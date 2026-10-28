"""Journal quotas through the public runner; no board required."""
from stm32_gdbtest import case, CheckFailed, RecordError


def exhaust(t):
    # Подробности исчерпываются, но проверки и вызовы продолжаются.
    for i in range(20):
        t.record('sample', dict(index=i))
    try:
        t.records()
    except RecordError as error:
        t.check('partial journal refused', error.code, 'incomplete_evidence')
    else:
        t.check('partial journal refused', False, True)
    t.check('prefix size', len(t.records(require_complete=False)), 3)


@case('HW_JOURNAL_PREFIX', timeout_s=20, labels=('emulator',))
def prefix(t):
    exhaust(t)
    t.check('checks continue', 1, 1)


@case('HW_JOURNAL_FAIL', timeout_s=20, labels=('emulator',))
def failed(t):
    exhaust(t)
    try:
        t.check('primary failure after truncation', False, True)
    except CheckFailed:
        pass


@case('HW_JOURNAL_INVALID', timeout_s=20, labels=('emulator',))
def invalid(t):
    exhaust(t)
    t.record('invalid after truncation', object())


@case('HW_JOURNAL_MMIO', timeout_s=20, labels=('emulator',))
def mmio(t):
    # Область памяти Renode подтверждает результат операций после усечения.
    for i in range(5):
        t.mmio.write('MODEL.RW', i)
        t.check('read after write', t.mmio.read('MODEL.RW'), i)


@case('HW_JOURNAL_LIVE', timeout_s=20, labels=('emulator',))
async def live(t):
    exhaust(t)
    t.resume(sync=False)
    t.check('wait after truncation', (await t.wait(timeout=0.05))['outcome'], 'timeout')
    t.check('halt after truncation', (await t.halt(timeout=2))['outcome'], 'stopped')
