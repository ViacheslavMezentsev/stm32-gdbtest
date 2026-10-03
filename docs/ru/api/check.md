# check

[API](index.md) · [English](../../en/api/check.md)

`check(name, actual, expected) -> None`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §4.1 |
| API_VERSION | 1 |

## Контракт

Сравнивает actual и expected через ==, записывает и печатает результат. name — название проверки.

Несовпадение вызывает CheckFailed и завершает сценарий с FAIL. Используйте значения, пригодные для JSON-отчёта. Не возвращает bool.

## Пример

```python
target.check("initial count", target.value("board_adc_sequences"), 0)
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.1.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py).
- [value](value.md), [fields](fields.md).
