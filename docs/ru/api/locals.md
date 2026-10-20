# locals

[API](index.md) · [English](../../en/api/locals.md)

`locals(frame=None) -> dict; arguments(frame=None) -> dict`

**Доступен с:** 0.3.0 · **API 3 (0.5.0):** без изменений, `await` не нужен.

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
t.reach("app_step")
arguments = t.arguments()["values"]
t.check("mode argument", arguments["mode"], t.evaluate("APP_MODE_BLINK"))
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), п. 4.17.1, 4.17.2.
