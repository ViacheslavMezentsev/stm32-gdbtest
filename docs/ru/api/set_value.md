# set_value — удалённое имя

[API](index.md) · [English](../../en/api/set_value.md)

`set_value(expression, value) -> None`

Историческое описание поведения до 0.4.0; в новом сценарии используйте пример миграции ниже.

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §4.6 |
| API_VERSION | 1 |
| Статус | Доступен до 0.3.0 включительно; удалён из кандидата 0.4.0 (`API_VERSION=2`) |
| Миграция | `write(path, value)` возвращает результат и проверяет запись при доступном чтении SRAM |

## Назначение

Читает expression до записи, выполняет GDB set variable с value и читает после. Записывает expression/value/before/after в mutations.

## Контракт и ограничения

value вставляется в команду GDB; используйте число или корректное C-выражение. Не делает автоматическую проверку равенства или откат. Автор проверяет допустимость MMIO и HAL-предусловия; чтение также может менять регистр.

## Пример миграции

```python
saved = t.read("board_adc_sequences")
try:
    t.write("board_adc_sequences", 0)
    t.check("counter injected", t.read("board_adc_sequences"), 0)
finally:
    t.write("board_adc_sequences", saved)
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.6.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/firmware/profiles/f411ce/tests/board/test_sleep.py).
- [value](value.md), [check](check.md), [force_return](force_return.md).
