# fields

[API](index.md) · [English](../../en/api/fields.md)

`fields(expression, expected) -> None`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §4.3 |
| API_VERSION | 1 |

## Контракт

expected — отображение пути поля в int или строковое C-выражение. Поля читаются и сравниваются последовательно в порядке отображения.

Строка ожидания вычисляется через value, а не сравнивается как текст. Первая ошибка/FAIL прекращает обход. Это несколько чтений, не атомарный снимок.

## Пример

```python
target.reach("HAL_GPIO_Init")
target.fields("*GPIO_Init", {"Pin": 1 << 5, "Mode": "GPIO_MODE_OUTPUT_PP"})
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.3.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/hal-f030/profile/tests/board/test_hal_methods.py).
- [check](check.md), [value](value.md).
