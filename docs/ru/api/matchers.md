# within, near, one_of, matches

[API](index.md) · [English](../../en/api/matchers.md)

`within(low, high)`, `near(value, tolerance)`, `one_of(*options)`, `matches(pattern)` — `from stm32_gdbtest import within, near, one_of, matches`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро); импорт без GDB |
| Контракт принят в ТЗ API | ревизия 0.3.4, п. 4.1.2 |
| API_VERSION | 1 |
| Основание | проверочная прошивка `tests/firmware`, сценарии `HW_CI_PROFILE`, `HW_CI_ADC_SERIES`, `HW_CI_ADC_UNITS` |

## Назначение

Ожидания для [check](check.md) помимо равенства: диапазон, допуск и набор вариантов. В отчёте
остаются фактическое значение и границы, а не `True`.

## Контракт и ограничения

- `within(low, high)` — числа (не `bool`), `low <= high`; проходит `low <= actual <= high`.
- `near(value, tolerance)` — число и неотрицательный допуск; проходит `abs(actual - value) <= tolerance`.
- `one_of(*options)` — хотя бы один вариант; проходит, если `actual` равно одному из них.
- `matches(pattern)` — регулярное выражение Python; проходит, если `actual` — строка и `re.search` находит
  совпадение (для привязки к началу или концу используйте `^` и `$`). Неверный шаблон — `invalid_pattern`.

Нечисловое `actual` у `within`/`near` — несовпадение, а не исключение Python. Неверные границы,
отрицательный допуск или пустой набор — `ApiError` операции `check` уже при создании сопоставителя
(`invalid_bounds`, `invalid_tolerance`, `invalid_options`). Сопоставитель можно хранить в константе
модуля и использовать в нескольких проверках и в строках таблицы.

## Пример

```python
from stm32_gdbtest import case, matches, near, one_of, within

PLAUSIBLE_VDDA_MV = within(2800, 3600)

t.check("VDDA, mV", t.read("board_adc_reading.vdda_mv"), PLAUSIBLE_VDDA_MV)
t.check("core clock", t.read("SystemCoreClock"), near(16_000_000, 160_000))
t.check("quality", t.read("board_adc_reading.quality"), one_of(1, 2, 3))
t.check("version", t.evaluate("app_info.version", as_type=str), matches(r"^v1\.\d+\.\d+"))
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.5, п. 4.1.2.
- [check](check.md).
