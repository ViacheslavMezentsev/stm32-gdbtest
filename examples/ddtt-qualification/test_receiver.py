"""Проверка отправителя; независимый журнал приёмника обрабатывает организатор."""
from stm32_gdbtest import case
import hashlib
import json


@case('HW_QUALIFICATION_PREFLIGHT', timeout_s=15, labels=('emulator',))
def preflight(t):
    t.reach('ready')
    t.check('preflight sends', t.read('sent'), 3)
    t.record('sender', {'sent': t.read('sent')})


def observe(t, expected):
    # Используем захваченные данные, а не изменяемый файл с диска.
    data = t.profile.data['qualification']
    payload = data['snapshot_json']
    checksum = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    if data['schema'] != 1 or checksum != data['snapshot_sha256']:
        raise ValueError('Invalid qualification data')
    t.record('qualification_input', {
        'snapshot': json.loads(payload), 'snapshot_sha256': checksum,
        'data_sha256': t.profile.files['data.qualification']['sha256']})
    t.reach('ready')
    # Сначала независимая проверка и журнал: check останавливает сценарий при FAIL.
    t.check('initialized', t.read('initialized'), 1)
    t.record('sender', {'sent': t.read('sent'), 'initialized': t.read('initialized')})
    # Счётчик не доказывает доставку: этому утверждению нужен допуск приёмника.
    t.check('three sends', t.read('sent'), expected)


@case('HW_QUALIFICATION', timeout_s=15, labels=('emulator',))
def sender(t):
    observe(t, 3)


@case('HW_QUALIFICATION_FAIL', timeout_s=15, labels=('emulator',))
def sender_fail(t):
    # Намеренный отказ: records сохраняется, исходный FAIL не исправляется.
    observe(t, 4)
