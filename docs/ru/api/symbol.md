# symbol

[API](index.md) · [English](../../en/api/symbol.md)

`symbol(name) -> dict`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | ревизия 0.3.3 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | проверочная прошивка `tests/firmware`, сценарии HW_CI_PROFILE, HW_CI_POINT_BUDGET |

## Назначение

Адрес, размер, тип и секция глобального или статического символа без ручных `&x` и `sizeof`.

## Контракт и ограничения

Возвращает `{"operation": "symbol", "name", "kind", "address", "size", "type", "section"}`.
`kind` — `variable` или `function`; размер функции — длина её лексического блока (или `None`), размер
переменной — `sizeof` типа. `section` берётся из `info symbol` и может быть `None`. Ищутся только
глобальные и статические символы; локальные переменные читает `locals`. Отсутствующий символ —
`ApiError` (`symbol_absent`).

## Пример

```python
state = t.symbol("app_state")
t.check("app_state in .bss", state["section"], ".bss")
t.check("app_state size", state["size"], t.evaluate("sizeof(app_state)"))
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.3, п. 4.15.1.
