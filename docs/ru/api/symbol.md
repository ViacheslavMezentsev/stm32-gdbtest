# symbol

[API](index.md) · [English](../../en/api/symbol.md)

`symbol(name) -> dict`

**Доступен с:** 0.3.0 · **API 3 (0.5.0):** без изменений, `await` не нужен.

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

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), п. 4.15.1.
