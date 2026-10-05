# ApiError

[API](index.md) · [English](../../en/api/api-error.md)

`ApiError(Exception): error.details; error.code; error.__cause__`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | не принят; проектируемая ревизия 0.2.8 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | согласованная проверочная прошивка `tests/firmware` и её сценарии |

## Назначение

Описывает отказ операции API раздельно: что делали (`operation`), на каком шаге (`stage`), с каким
наблюдаемым эффектом (`effect`) и почему (`code`). Исходная ошибка отладчика сохраняется как причина.

## Контракт и ограничения

`details` всегда содержит `operation`, `stage`, `effect` и `code`; дополнительные поля операции
добавляются в тот же словарь. `code` доступен и как свойство.

Ограничения: словарь операций закрыт (`read`, `write`, `eval`, `registers`, `frames`, `breakpoint`,
`watch`, `resume`, `reach`, `step`, `until`, `finish`, `ret`, `call`, `reset`, `execute`, `record`,
`records`, `config`); шаги — `validation`, `command`, `observe`, `readback`; эффекты — `none`,
`unknown`, `partial`, `applied`. `effect` сообщает только наблюдаемый эффект, отказ не откатывает уже
выполненные действия. Полный перечень кодов формируется по мере реализации методов.

## Пример

```python
try:
    t.ret(1 << 40)
except ApiError as error:
    t.check("operation", error.details["operation"], "ret")
    t.check("effect is known or unknown", error.details["effect"] in ("none", "unknown"), True)
```

Ошибка операции отличается от несовпадения проверки: первая — `ApiError`, второе — `CheckFailed`.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.2.7.
