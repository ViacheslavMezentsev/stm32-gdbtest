# memory

[API](index.md) · [English](../../en/api/memory.md)

`memory(address, size) -> bytes; write_memory(address, data, *, verify=True) -> dict`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | ревизия 0.3.3 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | проверочная прошивка `tests/firmware`, сценарии HW_CI_PROFILE |

## Назначение

Сырые байты буферов и образа: снимки, CRC, сигнатуры.

## Контракт и ограничения

`memory` читает от 1 до 4096 байт в окне SRAM (`0x20000000..0x20100000`) или Flash профиля
(`flash_start`, `flash_size`). `write_memory` пишет только в SRAM, читает обратно и записывает изменение
в `report["mutations"]` (байты в hex). Адреса периферии отвергаются (`outside_window`): чтение
регистра может изменить состояние устройства. Неверный блок — `invalid_block`, отказ GDB —
`read_failed`/`write_failed`, расхождение после записи — `verification_failed`.

## Пример

```python
vectors = target.memory(target.profile["flash_start"], 8)
target.check("initial SP in SRAM", 0x20000000 <= int.from_bytes(vectors[:4], "little") < 0x20100000, True)
address = target.symbol("app_state")["address"]
target.write_memory(address, bytes(4))
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.3, п. 4.16.1–4.16.3, 6.8.
