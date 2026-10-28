"""Report quota acceptance with real navigation and independent failures."""
from stm32_gdbtest import case, CheckFailed


def checks(t):
    # Первые строки остаются, последующие проверки продолжают выполняться.
    for i in range(12):
        t.check('after report limit', i, i)


@case('HW_REPORT_QUOTA_PASS', timeout_s=20, labels=('emulator',))
def passed(t):
    checks(t)
    t.record('finished', True)


@case('HW_REPORT_QUOTA_FAIL', timeout_s=20, labels=('emulator',))
def failed(t):
    checks(t)
    try:
        t.check('failure outside stored prefix', False, True)
    except CheckFailed:
        pass


@case('HW_REPORT_QUOTA_MIXED', timeout_s=20, labels=('emulator',))
def mixed(t):
    checks(t)
    for i in range(12):
        t.record('samples', i)


@case('HW_REPORT_QUOTA_LIVE', timeout_s=30, labels=('emulator',))
async def live(t):
    checks(t)
    for i in range(6):
        t.resume(sync=False)
        t.check('wait', (await t.wait(timeout=0.01))['outcome'], 'timeout')
        t.check('halt', (await t.halt(timeout=2))['outcome'], 'stopped')
