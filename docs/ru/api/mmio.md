# mmio.read / mmio.write

[API](index.md) · [English](../../en/api/mmio.md)

`t.mmio.read(name, *, allow_effects=False, override=None, reason=None) -> int`; `t.mmio.write(name, value, *, allow_effects=False, override=None, reason=None) -> dict`

**Доступен с:** 0.5.0 · **API 3 (0.5.0):** новое в 0.5.0; `await` не нужен; нужен SVD в `session.toml` (`[mmio] svd`).

```python
value = t.mmio.read("GPIOA.IDR")
ack = t.mmio.write("GPIOA.BSRR", 1)
```

Имена — точные имена регистров из [снимка SVD](../SVD.md), не выражения GDB.
Сигнатуры: `read(name, *, allow_effects=False, override=None, reason=None) -> int`,
`write(name, value, *, allow_effects=False, override=None, reason=None) -> dict`.
Чтение возвращает беззнаковое целое. Запись принимает только Python int (не bool),
помещающийся в ширину; возвращает `address`, `width` в битах, `value`,
`acknowledged=True`, `verified=False`. ACK подтверждает ответ сервера, не состояние устройства.

## Проверки до доступа

SVD задаёт адрес, ширину 8/16/32, права и эффекты. Проверяются выравнивание,
32-битный диапазон адресов, диапазон значения, права регистра и всех полей.
Отсутствующие права, перекрывающиеся поля и неподдержанные описания отвергаются.
Наличие WO-поля запрещает чтение всего регистра; RO-поля — запись.
Запись writeOnce/read-writeOnce запрещена: история неизвестна. writeConstraint
запрещает запись до появления отдельной реализации ограничений.
Любой описанный readAction или modifiedWriteValues (в том числе поля) требует
`allow_effects=True`. Это согласие не отменяет остальные проверки.

Нужны Cortex-M little-endian, основной поток Python GDB, остановленные потоки
выбранного inferior и RemoteTargetConnection.send_packet. Проверка выполняется
перед каждой операцией; нет пользовательского флага «транспорт проверен».
Периферия и DMA могут продолжать работать при остановленном ядре.

## Транспорт и ошибки

Одна принятая операция вызывает send_packet один раз: RSP `m` при чтении или `M`
при записи, минуя кэш памяти и вычисление выражений GDB. Нет before, readback, RMW,
повторной попытки и автоматического восстановления. Ответ чтения должен содержать
ровно заданное число байт, записи — `OK`.

Гарантия заканчивается на запросе к GDB: ширина/число физических транзакций сервера,
преобразования адаптера и повторы внутри транспорта GDB не гарантируются.
SVD также может быть ошибочным. Проверяйте маршрут в Renode и отдельно на целевом
стенде по [методике MMIO](../MMIO.md); PASS модели не означает HW PASS.

`MMIOError` — подкласс ApiError, доступен из stm32_gdbtest. `details` содержит
operation=`mmio.read`/`mmio.write`, code, stage, effect; причина сохраняется в __cause__.
До доступа effect=none, stage=validation (включая unqualified_context).
Ошибка/короткий ответ после отправки: transport_failed, stage=transport, effect=unknown.
Не повторяйте такую операцию автоматически: чтение уже могло извлечь FIFO.

В журнал до отправки добавляется mmio.attempt с исходным и эффективным описанием,
SHA-256 SVD, причиной override и значением записи; после — mmio.result.
Отказы валидации не являются попытками транспорта и в эти записи не входят.
Ошибка журнала до отправки: journal_unavailable/audit/none; после: audit/unknown.
Две записи расходуют общие лимиты records; включите `[results] capture = true`,
чтобы runner сохранил журнал в records.json, включая ERROR. Без capture журнал
существует только в памяти сценария. Исчерпание лимита не скрывается.

## Исправление ошибочного SVD

```python
from stm32_gdbtest import MMIORegister
reg = MMIORegister("MODEL.WO", 0x40000004, 32, "write-only")
t.mmio.write("MODEL.WO", 7, override=reg,
                  reason="Учебная модель поддерживает запись; ошибка исходного SVD")
```

MMIORegister — неизменяемое описание: name, address, width, access,
read_action=None, write_effect=None, fields=(), constraint=False.
Каждое поле — кортеж (name, bit_offset, bit_width, access, read_action, write_effect, constraint).
Override требует непустую причину и совпадение имени, допускается без SVD.
Он заменяет описание целиком, но не снимает проверки адреса, ширины, прав,
эффектов, остановки, транспорта и журнала. `safety=False` и строковые присваивания отсутствуют.

## Воспроизводимая проверка

[Учебная модель и команды](../../../tests/mmio-renode/README.md): WO, RTC, FIFO, W1C,
8/16/32 бита, наследование, потеря ACK, неверный SVD. Host-регрессия:
`python -m unittest discover -s tests/host -p test_mmio.py`.

Соединение должно обслуживать ровно один inferior: прямой пакет не выбирает процесс многопроцессного remote-сервера.

Аппаратная приёмка 16.10.2026: шесть MCU, 141 проверка выбранного 32-битного GPIO/DMA маршрута, recovery VERIFIED. Границы и матрица — [API_ACCEPTANCE](../API_ACCEPTANCE.md).

## Обоснование и двойной отказ (кандидат 0.6.0)

`reason` разрешён и без `override`: непустая строка сохраняется в `mmio.attempt`,
не меняя SVD, права и согласие на эффекты. Пустое/нестроковое значение без override
даёт `invalid_reason` до транспорта; override по-прежнему требует обоснования.
Если транспорт и запись результата отказали вместе, наружу передаётся
`transport_failed` (transport/unknown), исходная причина в `__cause__`,
ошибка аудита отдельно в `details.audit_error`. Повтора доступа нет.
Если транспорт не отказал, прежние `journal_unavailable` и effect=none/unknown
до/после обращения сохраняются. ACK не доказывает физический эффект.
