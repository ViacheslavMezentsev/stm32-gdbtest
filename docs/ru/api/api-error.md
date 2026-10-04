# api-error

[API](index.md) · [English](../../en/api/api-error.md)

`ApiError(Exception): error.details; error.__cause__`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | не выпущено: проект пакета 0.3.0 |
| Контракт принят в ТЗ API | не принят; проектируемая ревизия 0.2.5 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | согласованная проверочная прошивка `tests/firmware` и её сценарии (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Назначение

Описывает отказ операции API раздельно: что делали, на каком шаге, с каким эффектом и почему.

## Контракт и ограничения

Поля `operation`, `stage`, `effect`, `code` и подробности доступны через `details`; исходная ошибка
отладчика сохраняется как причина.

Ограничения: полный перечень кодов и формулировок ещё согласуется; `effect` сообщает только
наблюдаемый эффект (`none`, `unknown`, `partial`, `applied`); отказ не откатывает уже выполненные
эффекты.

## Пример

```python
try:
    target.write("app_state.ticks", 1 << 40)
except ApiError as error:
    target.check("operation", error.details["operation"], "write")
```

Отказ операции отличается от несовпадения проверки: первое — `ApiError`, второе — `CheckFailed`.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.2.5.
