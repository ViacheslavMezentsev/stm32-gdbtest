# CheckFailed

[API](index.md) · [English](../../en/api/check-failed.md)

`CheckFailed(ApiError, AssertionError): error.name; error.details`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | не принят; проектируемая ревизия 0.2.8 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | согласованная проверочная прошивка `tests/firmware` и её сценарии |

## Назначение

Сообщает, что проверка сценария не совпала с ожиданием, и попадает в отчёт как провал проверки.

## Контракт и ограничения

Исключение содержит имя проверки (`name`) и её данные в `details` (`check`, `actual`, `expected`,
`code=mismatch`). Совместимость сохранена: `CheckFailed` остаётся подклассом `AssertionError` и
`ApiError`, поэтому прежние сценарии, перехватывающие `AssertionError`, продолжают работать.

Ограничения: провал проверки не прерывает прогон немедленно, если сценарий продолжает работу, но
итог прогона — провал; `actual` и `expected` попадают в `details` как есть и должны быть
сериализуемы отчётом.

## Пример

```python
t.check("ticks advanced", t.value("app_state.ticks") > 0, True)
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.2.7.
