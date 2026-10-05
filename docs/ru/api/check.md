# check

[API](index.md) · [English](../../en/api/check.md)

`check(name, actual, expected=<истина>) -> None`; `check(rows) -> int`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | сравнение: 0.1.0rc1 / v0.1.0-rc.1; сопоставители, проверка истинности и таблица: 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | 0.1.0, п. 4.1.1; ревизия 0.3.4, п. 4.1.2–4.1.4 |
| API_VERSION | 1 |
| Основание | проверочная прошивка `tests/firmware`, все сценарии |

## Назначение

Записывает одну проверку в отчёт, печатает PASS/FAIL и при несовпадении завершает сценарий с FAIL.

## Контракт и ограничения

Вид проверки определяется аргументами:

| Вызов | Проходит, если | `expected` в отчёте |
| :--- | :--- | :--- |
| `check(name, actual, expected)` | `actual == expected` | значение |
| `check(name, actual, within(low, high))` | `low <= actual <= high` | `{"low", "high"}`, `kind="range"` |
| `check(name, actual, near(value, tolerance))` | `abs(actual - value) <= tolerance` | `{"value", "tolerance"}`, `kind="near"` |
| `check(name, actual, one_of(a, b, …))` | `actual` равно одному из вариантов | `{"in": [...]}`, `kind="in"` |
| `check(name, actual)` | `actual` истинно | `True`, `kind="truth"` |
| `check(rows)` | все строки таблицы проходят по порядку | запись на каждую строку |

Список или кортеж в `expected` сравнивается на равенство, как раньше: массив из `read` остаётся
массивом. Строка таблицы — `(name, actual, expected)` или `(name, actual)`; строковые ячейки `actual`
и `expected` вычисляются как выражения GDB через `evaluate`, `expected` может быть сопоставителем.
Структура всех строк проверяется до первой оценки, первое несовпадение останавливает таблицу.

Несовпадение — `CheckFailed`. Ошибка в аргументах (пустое имя, неверные границы сопоставителя,
пустая таблица) — `ApiError` операции `check` без записи в отчёт. Значения должны быть пригодны для
JSON-отчёта.

## Пример

```python
from stm32_gdbtest import case, near, one_of, within

t.check("initial count", t.read("board_adc_sequences"), 0)
t.check("VDDA, mV", t.read("board_adc_reading.vdda_mv"), within(2800, 3600))
t.check("die temperature, mdegC", t.read("board_adc_reading.temperature_mdeg_c"), near(30_000, 15_000))
t.check("stand backend", t.profile.stand["backend"], one_of("openocd", "jlink"))
t.check("GPIOA clock", t.read("RCC->AHBENR & RCC_AHBENR_GPIOAEN"))
t.check([
    ("PA5 output", "GPIOA->MODER & GPIO_MODER_MODER5", "GPIO_MODER_MODER5_0"),
    ("DMA channel", "DMA1_Channel1->CCR", "DMA_CCR_MINC | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_0 | DMA_CCR_TCIE | DMA_CCR_TEIE"),
    ("timer running", "TIM3->CR1 & TIM_CR1_CEN"),
])
```

Ожидание, которое следует из устройства (биты регистра, номер прерывания), записывается
идентификатором из прошивки; физические величины (частоты, делители, номера каналов) задаются в
сценарии независимо (TECH-001).

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.4, п. 4.1.1–4.1.4.
- [Сопоставители](matchers.md), [read](read.md), [evaluate](evaluate.md).
