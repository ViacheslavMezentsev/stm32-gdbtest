# resume

[API](index.md) · [Русский](../../ru/api/resume.md)

`resume(*, sync=True) -> dict`; in `async def` use `await t.resume()` or `t.resume(sync=False)`

**Available since:** 0.3.0; `sync=False` since 0.5.0 · **API 3 (0.5.0):** in `async def` the blocking form is awaited; `resume(sync=False)` is `async def` only and opens a live window.

## Purpose

Continues target execution. `resume()` in `def` (and `await t.resume()` in `async def`) waits for a stop
and returns `operation="resume"`, `outcome="stopped"` and the `stop` description. `resume(sync=False)`
lets the target go and returns `outcome="started"` and the window number `generation` at once; it does
not guarantee that the target is still running when it returns.

## Contract and limitations

- A stop needs a point: [breakpoint](breakpoint.md), [watch](watch.md) or a [reach](reach.md) condition;
  without one, a blocking `resume()` is bounded only by the scenario timeout.
- After `resume(sync=False)` and until a stop, `read`, `write`, `memory`, `evaluate`, `t.mmio`, `call`,
  navigation and `execute` are refused. `record`, `check` of ready values and Python code are allowed.
- In `def` the `sync=False` form is refused (`async_required`); `sync` must be a `bool` (`invalid_sync`).
- A new `resume` clears the previous stop. Host time of the window is not a measurement of MCU time.

## Example

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

## Avoid

```python
await t.reach("idle")
t.resume(sync=False)
value = t.read("counter")            # refused: the target is running
```

## References

- [Live execution window](../LIVE_EXECUTION.md), [VTOR/FPB observer](../LIVE_OBSERVER.md).
- [API specification](../../TECHNICAL_SPECIFICATION_API.md) (Russian), items 4.5, 4.22.
- [resume](resume.md), [wait](wait.md), [halt](halt.md).
