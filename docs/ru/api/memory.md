# memory

[API](index.md) · [English](../../en/api/memory.md)

> **MMIO:** Метод ограничен окнами SRAM/Flash и не является обходом для доступа к MMIO. Не расширяйте окна профиля ради периферии. [Ограничения и проверка на модели/плате](../MMIO.md).

`memory(address, size | data, *, verify=None) -> bytes | dict`

**Доступен с:** 0.3.0 · **API 3 (0.5.0):** без изменений, `await` не нужен.

## Назначение

Сырые байты буферов и образа: снимки, CRC, сигнатуры, восстановление сохранённого состояния.

## Контракт и ограничения

Операцию определяет тип второго аргумента:

| Второй аргумент | Операция | Результат |
| :--- | :--- | :--- |
| `int` (не `bool`), 1..4096 | чтение стольких байт из окна SRAM или Flash профиля | `bytes` |
| `bytes`, `bytearray`, `memoryview` | запись байт в SRAM; чтение обратно, если не `verify=False`; запись в `report["mutations"]` | `{"operation": "memory", "address", "size", "verified"}` |
| всё остальное (`str`, `list`, `bool`, `float`) | отказ до обращения к памяти (`invalid_block`) | — |

Список чисел не принимается: ширина элемента была бы догадкой. Байты собираются явно:
`value.to_bytes(4, "little")`, `struct.pack("<HI", a, b)`, `bytes(8)`. `verify` относится только к
записи; вместе с размером он даёт отказ (`invalid_verify`).

Окно SRAM — `0x20000000..0x200FFFFF`; окно Flash берётся из `flash_start` и `flash_size` профиля и
доступно только для чтения. Адреса периферии отвергаются (`outside_window`): чтение регистра может
изменить состояние устройства. Отказ GDB — `read_failed`/`write_failed`, расхождение после записи —
`verification_failed` с `effect="applied"`.

## Пример

```python
state = t.symbol("app_state")
snapshot = t.memory(state["address"], state["size"])      # чтение: bytes
t.call("app_step", "&app_state", "APP_MODE_BLINK")
t.memory(state["address"], snapshot)                     # запись: восстановить сохранённые байты
vectors = t.memory(t.profile["flash_start"], 8)
initial_sp = int.from_bytes(vectors[:4], "little")  # A stack-top pointer, not a readable byte address.
```

Проверка начального SP и границ чтения различается: [TECH-017](../TESTING_TECHNIQUES.md#tech-017).

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), п. 4.16.1–4.16.4, 6.8.
- [symbol](symbol.md), [write](write.md).

## Полнота чтения (0.5.0)

`memory(address, size)` возвращает ровно size байтов. Иная длина ответа вызывает ApiError
с code=incomplete_read, operation=memory, stage=readback, effect=none и полями address,
requested, actual. Частичный снимок не возвращается; проверка не пишет в память.
Это не проверяет, правильно ли сценарий определил размер объекта: размер из DWARF остаётся
предусловием. Короткий ответ транспорта воспроизведён только host-инъекцией.
