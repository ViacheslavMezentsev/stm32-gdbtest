"""Штатные сценарии нейтральной модели: успех, намеренный отказ и зависание."""
from stm32_gdbtest import case


@case('HW_EMU_STARTUP', timeout_s=15, labels=('emulator',))
def startup(t):
    t.reach('observe')
    t.check('counter initialized', t.read('counter'), 3)
    t.record('state', {'counter': t.read('counter')})


@case('HW_EMU_FAIL', timeout_s=15, labels=('emulator',))
def failure(t):
    t.reach('observe')
    t.check('intentional failure', t.read('counter'), 4)


@case('HW_EMU_TIMEOUT', timeout_s=2, labels=('emulator',))
def timeout(t):
    # Зависание Python, чтобы проверить внешний надзор runner.
    import time
    time.sleep(30)


@case('HW_EMU_RESET', timeout_s=15, labels=('emulator',))
def reset_refused(t):
    from stm32_gdbtest import ApiError
    try:
        t.reset()
    except ApiError as error:
        t.check('reset refused before command', error.code, 'unsupported_backend')
    else:
        t.check('reset must be refused', False, True)
