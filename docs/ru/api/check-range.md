# check_range

[API](index.md) · [English](../../en/api/check-range.md)

`check_range(name, actual, low, high); check_near(name, actual, expected, tolerance); check_in(name, actual, options)`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | ревизия 0.3.3 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | проверочная прошивка `tests/firmware`, сценарии HW_CI_PROFILE, HW_CI_ADC_SERIES |

## Назначение

Проверки с границами: в отчёте остаются фактическое значение и границы, а не `True`.

## Контракт и ограничения

- `check_range`: проходит при `low <= actual <= high`; `expected` в отчёте — `{"low", "high"}`.
- `check_near`: проходит при `|actual - expected| <= tolerance`; `expected` — `{"value", "tolerance"}`.
- `check_in`: проходит, если `actual` равно одному из `options` (непустые list/tuple/set); `expected` — `{"in": [...]}`.

Запись в `report["checks"]` получает поле `kind` (`range`, `near`, `in`). Нечисловое `actual` в
`check_range`/`check_near` — несовпадение (`CheckFailed`), а не исключение Python. Неверные границы,
отрицательный допуск или пустой набор — `ApiError` операции `check` (`invalid_bounds`,
`invalid_tolerance`, `invalid_options`) без записи в отчёт.

## Пример

```python
vdda = target.read("sensor.vdda_mv")
target.check_range("VDDA, mV", vdda, 2900, 3600)
target.check_near("temperature, C", target.evaluate("sensor.temp", as_type=float), 25.0, 15.0)
target.check_in("mode", target.read("app_mode"), ("APP_MODE_IDLE", "APP_MODE_BLINK"))
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.3, п. 4.1.2.
