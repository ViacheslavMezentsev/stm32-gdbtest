# CheckFailed

[API](index.md) · [English](../../en/api/check-failed.md)

`CheckFailed(ApiError, AssertionError): error.name; error.details`

**Доступен с:** 0.1.0-rc.1; публичный импорт — 0.3.0 · **API 3 (0.5.0):** без изменений, `await` не нужен.

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
t.check("ticks advanced", t.read("app_state.ticks") > 0, True)
```

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md).
