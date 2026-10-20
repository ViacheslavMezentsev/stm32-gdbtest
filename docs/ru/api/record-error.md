# RecordError

[API](index.md) · [English](../../en/api/record-error.md)

`RecordError(ValueError)`

**Доступен с:** 0.3.0 · **API 3 (0.5.0):** без изменений, `await` не нужен.

## Назначение

Публичное исключение валидации record/records; импортируется из stm32_gdbtest без GDB. Поля code и limit описывают категорию отказа.

## Контракт и ограничения

code: invalid_name, unsupported_type, invalid_text, non_finite, cycle, limit_exceeded. limit для limit_exceeded: records/nodes/depth/text_bytes/integer_bits; иначе None. Текст и приоритет ошибок не фиксированы. Необработанное исключение даёт ERROR; MemoryError не подменяется.

## Пример

```python
from stm32_gdbtest import RecordError

try:
    t.record("", 1)
except RecordError as error:
    t.check("invalid name rejected", error.code, "invalid_name")
else:
    t.check("invalid name accepted", True, False)
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §5.6.
- [Реализация](../../../stm32_gdbtest/records.py).
- [Сценарий или проверка реализации](../../../tests/host/test_record_errors.py).
- [record](record.md), [records](records.md).
