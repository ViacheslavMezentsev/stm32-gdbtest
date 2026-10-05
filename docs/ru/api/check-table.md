# check_table

[API](index.md) · [English](../../en/api/check-table.md)

`check_table(rows) -> int`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | ревизия 0.3.3 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | проверочная прошивка `tests/firmware`, сценарии HW_CI_INIT, HW_CI_LED_GPIO (all profiles) |

## Назначение

Табличная проверка строк «имя, фактическое, ожидаемое» без локальных помощников в сценариях.

## Контракт и ограничения

`rows` — непустой list/tuple строк из трёх элементов. Строковые ячейки `actual` и `expected`
вычисляются как выражения GDB через `evaluate` (объявленный тип), остальные используются как есть.
Строки проверяются по порядку через `check`; первое несовпадение останавливает сценарий
(`CheckFailed`). Структура строк проверяется до первой оценки (`ApiError`, `invalid_rows`).
Возвращает число проверенных строк.

## Пример

```python
target.check_table([
    ("initialized interval", "app_delay", "EXPECTED_DELAY"),
    ("BSS loop count", "app_state.ticks", 0),
    ("PA5 output", "(GPIOA->MODER & GPIO_MODER_MODER5) == GPIO_MODER_MODER5_0", 1),
])
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.3, п. 4.1.3.
