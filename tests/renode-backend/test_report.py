"""Report acceptance: completed events, middle failure and live-window diagnostics."""
from stm32_gdbtest import case, CheckFailed


async def series(t, count):
    # Реальная остановка и записи RAM дополняют длинную последовательность проверок.
    await t.reach('observe')
    for value in range(3):
        t.write('counter', value)
    for value in range(count):
        t.check('sequence', value, value)


@case('HW_REPORT_1000', timeout_s=60, labels=('emulator',))
async def report_1000(t):
    await series(t, 1000)


@case('HW_REPORT_10000', timeout_s=60, labels=('emulator',))
async def report_10000(t):
    await series(t, 10000)


@case('HW_REPORT_SWALLOWED', timeout_s=15, labels=('emulator',))
def swallowed(t):
    # Перехваченный отказ в середине нельзя потерять при упаковке истории.
    for index in range(1000):
        try:
            t.check('middle', index != 500, True)
        except CheckFailed:
            pass


@case('HW_REPORT_LIVE', timeout_s=15, labels=('emulator',))
async def live(t):
    t.resume(sync=False)
    t.check('timeout', (await t.wait(timeout=0.05))['outcome'], 'timeout')
    t.check('halt', (await t.halt(timeout=2))['outcome'], 'stopped')


@case('HW_REPORT_UNEXPECTED', timeout_s=15, labels=('emulator',))
async def unexpected(t):
    t.breakpoint('calculate')
    await t.reach('observe')


@case('HW_REPORT_STORAGE', timeout_s=15, labels=('emulator',))
def unavailable_storage(t):
    # Отказ временного файла после заполнения блока не заменяет первичный CheckFailed.
    buffer = t.report['checks']
    for index in range(256):
        t.check('spooled before failure', index, index)
    while len(buffer.pending) < 128:
        t.check('before storage failure', True, True)
    buffer.stream.close()
    t.check('primary storage control', False, True)


@case('HW_REPORT_JOURNAL', timeout_s=15, labels=('emulator',))
async def journal_limit(t):
    # Инъекция лимита собственного журнала при работающем ядре; cleanup обязан остановить цель.
    t.resume(sync=False)
    original = t._journal._limits
    t._journal._limits = (len(t._journal._entries), *original[1:])
    try:
        t.record('required sample', 1)
    finally:
        t._journal._limits = original


@case('HW_REPORT_JOURNAL_CAUGHT', timeout_s=15, labels=('emulator',))
def journal_caught(t):
    # Перехваченная потеря обязательной записи всё равно делает результат непригодным.
    from stm32_gdbtest import RecordError
    original = t._journal._limits
    t._journal._limits = (len(t._journal._entries), *original[1:])
    try:
        try:
            t.record('required sample', 1)
        except RecordError:
            pass
    finally:
        t._journal._limits = original


@case('HW_REPORT_LOST_FAIL', timeout_s=15, labels=('emulator',))
def lost_fail(t):
    # Подробная строка FAIL не помещается; перехваченный CheckFailed не должен стать PASS.
    from stm32_gdbtest import report_data
    original = report_data.MAX_ROWS
    report_data.MAX_ROWS = len(t.report['checks'])
    try:
        try:
            t.check('failed outside stored history', False, True)
        except CheckFailed:
            pass
    finally:
        report_data.MAX_ROWS = original
