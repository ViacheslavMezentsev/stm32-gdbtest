# resume

[API](index.md) · [English](../../en/api/resume.md)

`resume(*, sync=True) -> dict`; в `async def` — `await t.resume()` или `t.resume(sync=False)`

**Доступен с:** 0.3.0; `sync=False` — 0.5.0 · **API 3 (0.5.0):** в `async def` блокирующая форма ожидается через `await`; `resume(sync=False)` — только `async def`, открывает живое окно.

## Назначение

Продолжает выполнение цели. `resume()` в `def` (и `await t.resume()` в `async def`) ждёт остановки
и возвращает `operation="resume"`, `outcome="stopped"` и описание `stop`. `resume(sync=False)` отпускает
цель и сразу возвращает `outcome="started"` и номер окна `generation`; работа ли цель в момент
возврата, не гарантируется.

## Контракт и ограничения

- Для остановки нужна точка: [breakpoint](breakpoint.md), [watch](watch.md) или условие [reach](reach.md);
  без неё блокирующий `resume()` ограничен только таймаутом сценария.
- После `resume(sync=False)` до остановки отклоняются `read`, `write`, `memory`, `evaluate`, `t.mmio`,
  `call`, навигация и `execute`. `record`, `check` готовых значений и код Python разрешены.
- В `def` форма `sync=False` отклоняется (`async_required`); `sync` должен быть `bool` (`invalid_sync`).
- Новый `resume` очищает прежнюю остановку. Время окна на хосте не является измерением времени MCU.

## Пример

```python
with t.watch("app_state.ticks"):
    t.resume()                       # def: blocks until the watchpoint stops the core

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
await t.reach("idle")
t.resume(sync=False)
value = t.read("counter")            # refused: the target is running
```

## Ссылки

- [Живое окно выполнения](../LIVE_EXECUTION.md), [наблюдатель VTOR/FPB](../LIVE_OBSERVER.md).
- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), п. 4.5, 4.22.
- [resume](resume.md), [wait](wait.md), [halt](halt.md).
