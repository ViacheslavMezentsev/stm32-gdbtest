# ApiError

[API](index.md) · [English](../../en/api/api-error.md)

`ApiError(Exception): error.details; error.code; error.__cause__`

**Доступен с:** 0.3.0 · **API 3 (0.5.0):** добавлены коды `unawaited_operation`, `already_awaited`, `operation_timeout`, `halt_timeout`, `expression_call_forbidden`, `unsupported_async_command`, `call_incomplete`.

## Назначение

Описывает отказ операции API раздельно: что делали (`operation`), на каком шаге (`stage`), с каким
наблюдаемым эффектом (`effect`) и почему (`code`). Исходная ошибка отладчика сохраняется как причина.

## Контракт и ограничения

`details` всегда содержит `operation`, `stage`, `effect` и `code`; дополнительные поля операции
добавляются в тот же словарь. `code` доступен и как свойство.

Ограничения: словарь операций закрыт (`read`, `write`, `eval`, `registers`, `frames`, `breakpoint`,
`watch`, `resume`, `reach`, `step`, `until`, `finish`, `ret`, `call`, `reset`, `execute`, `record`,
`records`, `config`, `mmio.read`, `mmio.write`); шаги — `validation`, `command`, `observe`, `readback`, `transport`, `audit`; эффекты — `none`,
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

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md).

[MMIOError](mmio.md) уточняет границу effect=none/unknown и ошибки журнала.
