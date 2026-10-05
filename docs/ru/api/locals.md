# locals

[API](index.md) · [English](../../en/api/locals.md)

`locals(frame=None) -> dict; arguments(frame=None) -> dict`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | ревизия 0.3.3 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | проверочная прошивка `tests/firmware`, сценарии HW_CI_RETURN_VALUE, HW_CI_STEP_SOURCE |

## Назначение

Локальные переменные и аргументы кадра одним словарём.

## Контракт и ограничения

Возвращает `{"operation", "function", "values", "unavailable"}`. `frame` — `None` (самый
внутренний кадр), глубина `int` от него или объект кадра GDB. `locals` обходит блоки от внутреннего к
блоку функции, внутреннее имя перекрывает внешнее; аргументы в `locals` не входят. Оптимизированные и
непреобразуемые значения перечисляются в `unavailable`, а не дают исключение. Кадр без отладочной
информации — `no_debug_info`, отсутствующий кадр — `no_frame`.

## Пример

```python
target.reach("app_step")
arguments = target.arguments()["values"]
target.check("mode argument", arguments["mode"], target.evaluate("APP_MODE_BLINK"))
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.3, п. 4.17.1, 4.17.2.
