# refused

[API](index.md) · [English](../../en/api/refused.md)

`with t.refused(code, *, name=None, **details) as refusal: ...`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | ревизия 0.3.6, п. 4.19.1–4.19.3 |
| API_VERSION | 1 |
| Основание | проверочная прошивка `tests/firmware`, сценарии `HW_CI_CALL`, `HW_CI_EVALUATE`, `HW_CI_EXECUTE`, `HW_CI_FRAMES`, `HW_CI_REGISTERS`, `HW_CI_RESET`, `HW_CI_RET_VALUE`, `HW_CI_WATCH`, `HW_CI_POINT_BUDGET` |

## Назначение

Проверка ожидаемого отказа операции: тело блока `with` должно завершиться `ApiError` с кодом `code`.
Заменяет конструкцию `try/except ApiError/else` из пяти-шести строк.

## Контракт и ограничения

- Дополнительные именованные аргументы (`effect="none"`, `stage="validation"`, `width=32`) сравниваются
  с `error.details` вместе с кодом.
- Результат записывается одной проверкой: `actual` — найденные значения деталей, `expected` —
  ожидаемые, `kind="refused"`; имя по умолчанию — `refused: <code>`.
- Совпавший отказ подавляется и сохраняется в `refusal.error` (`refusal.details` — его детали), чтобы
  после блока проверить причину или журнал.
- Если тело выполнилось без исключения, проверка не проходит: `actual=None`.
- Отказ с другим кодом или деталями — несовпадение `CheckFailed`.
- `CheckFailed` и исключения, не являющиеся `ApiError`, проходят из блока без изменений.

## Пример

```python
with t.refused("unsupported_argument", effect="none", name="an unsupported argument is refused"):
    t.call("app_step", object())

with t.refused("command_failed") as failure:
    t.evaluate("api030_no_such_symbol")
t.check("причина сохранена", failure.error.__cause__ is not None)

for path, code in (("api030_no_such_object", "invalid_path"), ("app_state.ticks + 1", "not_addressable")):
    with t.refused(code, stage="validation"):
        t.watch(path)
```

Было:

```python
try:
    t.call("app_step", object())
except ApiError as error:
    t.check("unsupported argument code", error.details["code"], "unsupported_argument")
    t.check("unsupported argument effect", error.details["effect"], "none")
else:
    t.check("an unsupported argument must be refused", False, True)
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.3.6, п. 4.19.1–4.19.3.
- [api-error](api-error.md), [check](check.md).
