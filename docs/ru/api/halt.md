# halt

[API](index.md) · [English](../../en/api/halt.md)

`await halt(*, timeout) -> dict`

**Доступен с:** 0.5.0 · **API 3 (0.5.0):** новое в 0.5.0; только `async def`, `await`, таймаут обязателен.

## Назначение

Останавливает работающую цель и ждёт подтверждения. Возвращает `operation="halt"`, `outcome`
(`stopped` или `exited`), `generation` и `stop`. После `stopped` память снова доступна.

## Контракт и ограничения

- Interrupt отправляется только работающей цели; при уже остановленной цели повторного interrupt нет.
  SIGINT после нашего interrupt отмечается причиной `interrupt`; пришедшая одновременно точка
  останова сохраняет свою причину.
- Неподтверждённая остановка за `timeout` — ERROR `halt_timeout` с неизвестным эффектом; автоматического
  повтора нет.
- Останавливает цель, а не GDB-сервер. После сценария runner сам делает ограниченную попытку halt (2 с)
  и пишет `execution_cleanup`; это не восстановление SRAM, FPB или VTOR.
- В `def` отклоняется (`async_required`).

## Пример

```python
@case("HW_WINDOW", timeout_s=20)
async def window(t):
    await t.reach("idle")
    started = t.resume(sync=False)
    try:
        waited = await t.wait(timeout=0.2)
        t.check("no stop yet", waited["outcome"], "timeout")
    finally:
        stopped = await t.halt(timeout=2)
    t.check("same window", stopped["generation"], started["generation"])
    t.check("memory readable", t.read("counter"), 3)
```

## Не рекомендуется

```python
t.resume(sync=False)
waited = await t.wait(timeout=0.2)
await t.halt(timeout=2)              # skipped when wait raises: put halt into finally
```

## Ссылки

- [Живое окно выполнения](../LIVE_EXECUTION.md), [наблюдатель VTOR/FPB](../LIVE_OBSERVER.md).
- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), п. 4.22.
- [resume](resume.md), [wait](wait.md), [halt](halt.md).

## Ошибка исполнения и ошибка аудита (кандидат 0.6.0)

Ошибка записи `execution` не заменяет `fault_stop`, `signal_stop`, `state_unknown`
или ошибку halt. Первичное исключение сохраняет тип/code и получает
`details.audit_error`. Без первичной ошибки отказ аудита даёт
`ApiError(code="journal_unavailable", stage="audit")`: после continue эффект `applied`,
после подтверждённого результата — `completed`. Это не означает отсутствие воздействия.
В `result.json` отдельны `primary_error`, `audit_error`, `primary_cause` (при наличии)
и `execution_audit_errors`: первые 16 диагностик со state и исходом/первичной ошибкой;
`execution_audit_error_count` считает все отказы, без рекурсивного использования Journal.
При большем числе отказов детали последующих не сохраняются. Это не режим truncate журнала.

Runner останавливает цель независимо от свободного места в Journal. Если остановка
подтверждена и контекст call восстановлен, `execution_cleanup=VERIFIED`, даже если
аудит halt не записан: тогда есть `execution_cleanup_audit_error`, итог остаётся ERROR.
Неизвестное состояние или незавершённый call по-прежнему дают cleanup ERROR.
Не подменяйте первичную ошибку своим `finally`: отдельный `await halt()` тоже может
выбросить исключение; сохраняйте обе причины либо оставляйте аварийную остановку runner.
