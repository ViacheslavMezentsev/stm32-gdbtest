# RecordError

[API](index.md) · [English](../../en/api/record-error.md)

`RecordError(ValueError)`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.2.0.dev0 → 0.2.0rc1 |
| Контракт принят в ТЗ API | 0.2.0; публичный импорт уточнён в 0.2.1; §5.6 |
| API_VERSION | 1 |
| Основание | действующий контракт 0.1.0/0.2.0 и сценарии проверочной прошивки `tests/firmware` |
| Синоним прежнего имени | RecordError -> a subclass of ApiError (алиас действует без предупреждений до 1.0, удаление в 0.4.0) |

Новый пакет реализован; `0.2.0rc1` — локальный кандидат, не опубликованный стабильный релиз.

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
