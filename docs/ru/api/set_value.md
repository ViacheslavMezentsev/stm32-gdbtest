# set_value

[API](index.md) · [English](../../en/api/set_value.md)

`set_value(expression, value) -> None`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §4.6 |
| API_VERSION | 1 |
| Основание | действующий контракт 0.1.0/0.2.0 и сценарии проверочной прошивки `tests/firmware` |
| Синоним прежнего имени | set_value(expression, value) -> write(path, value) (алиас действует без предупреждений до 1.0, удаление в 0.4.0) |

## Назначение

Читает expression до записи, выполняет GDB set variable с value и читает после. Записывает expression/value/before/after в mutations.

## Контракт и ограничения

value вставляется в команду GDB; используйте число или корректное C-выражение. Не делает автоматическую проверку равенства или откат. Автор проверяет допустимость MMIO и HAL-предусловия; чтение также может менять регистр.

## Пример

```python
saved = target.value("board_adc_sequences")
try:
    target.set_value("board_adc_sequences", 0)
    target.check("counter injected", target.value("board_adc_sequences"), 0)
finally:
    target.set_value("board_adc_sequences", saved)
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.6.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/firmware/profiles/f411ce/tests/board/test_sleep.py).
- [value](value.md), [check](check.md), [force_return](force_return.md).
