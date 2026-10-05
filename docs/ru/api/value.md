# value

[API](index.md) · [English](../../en/api/value.md)

`value(expression) -> int`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §4.2 |
| API_VERSION | 1 |
| Устарел | с 0.3.0: одно предупреждение `deprecated` за прогон в `report["warnings"]`; замена — `read(path)` или `evaluate(expression)`; удаление в 0.4.0 (ТЗ API 6.7) |
| Основание | действующий контракт 0.1.0/0.2.0 и сценарии проверочной прошивки `tests/firmware` |
| Синоним прежнего имени | value(expression) -> read(path) (алиас действует без предупреждений до 1.0, удаление в 0.4.0) |

## Назначение

expression — строка выражения GDB/C в текущем контексте. Вычисляет выражение, загружает ленивое значение и преобразует в int.

## Контракт и ограничения

MCU должен быть остановлен для согласованного чтения. optimized-out и отсутствующие символы дают ошибку, не ноль. Это не типизированное чтение float/структур; выражение может иметь побочные эффекты.

## Пример

```python
sequence = t.value("board_adc_sequences")
t.check("nonnegative sequence", sequence >= 0, True)
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.2.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/firmware/common/tests/board/test_measurements.py).
- [check](check.md), [fields](fields.md), [record](record.md).
