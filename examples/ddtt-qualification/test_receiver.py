"""Проверка отправителя; независимый журнал приёмника обрабатывает организатор."""
from stm32_gdbtest import case


@case('HW_QUALIFICATION', timeout_s=15, labels=('emulator',))
def sender(t):
    t.reach('ready')
    # Счётчик не доказывает доставку: этому утверждению нужен допуск приёмника.
    t.check('three sends', t.read('sent'), 3)
    # Инициализация не зависит от способности приёмника принять посылку.
    t.check('initialized', t.read('initialized'), 1)
    t.record('sender', {'sent': t.read('sent'), 'initialized': t.read('initialized')})
