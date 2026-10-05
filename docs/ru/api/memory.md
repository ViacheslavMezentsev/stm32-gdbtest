# memory

[API](index.md) · [English](../../en/api/memory.md)

`memory(address, size | data, *, verify=None) -> bytes | dict`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | ревизия 0.3.4, п. 4.16.1–4.16.4, 6.8 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | проверочная прошивка `tests/firmware`, сценарии `HW_CI_PROFILE`, `HW_CI_CALL_PREDICATE` |

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
t.check("initial SP in SRAM", int.from_bytes(vectors[:4], "little"), within(0x20000000, 0x200FFFFF))
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.4, п. 4.16.1–4.16.4, 6.8.
- [symbol](symbol.md), [write](write.md).
