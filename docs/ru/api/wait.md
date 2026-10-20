# wait

[API](index.md) · [English](../../en/api/wait.md)

`await wait(*, timeout) -> dict`

**Доступен с:** 0.5.0 · **API 3 (0.5.0):** новое в 0.5.0; только `async def`, `await`, таймаут обязателен.

## Назначение

Пассивно ждёт остановки или выхода цели, открытых `resume(sync=False)`. Возвращает
`operation="wait"`, `outcome` (`stopped`, `exited` или `timeout`), `generation` и при остановке `stop`.

## Контракт и ограничения

- `timeout` — обязательное конечное положительное число секунд хоста (`invalid_timeout`).
- Таймаут — результат ожидания, а не FAIL и не остановка MCU: цель продолжает работать.
  Поэтому [halt](halt.md) ставится в `finally`.
- Не отправляет interrupt. Уже произошедшая остановка не теряется; для повторного ожидания той же
  остановки `generation` прежний. `exited` не разрешает читать память завершившейся цели.
- Остановка по fault guard или неожиданному сигналу даёт ApiError `fault_stop` / `signal_stop`.
- В `def` отклоняется (`async_required`); без `await` следующая операция отклоняется (`unawaited_operation`).

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
await t.wait(timeout=5)              # no finally/halt: a timeout leaves the target running
time.sleep(1)                        # blocks GDB event handling
```

## Ссылки

- [Живое окно выполнения](../LIVE_EXECUTION.md), [наблюдатель VTOR/FPB](../LIVE_OBSERVER.md).
- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), п. 4.22.
- [resume](resume.md), [wait](wait.md), [halt](halt.md).
