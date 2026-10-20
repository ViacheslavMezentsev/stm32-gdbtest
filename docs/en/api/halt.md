# halt

[API](index.md) · [Русский](../../ru/api/halt.md)

`await halt(*, timeout) -> dict`

**Available since:** 0.5.0 · **API 3 (0.5.0):** new in 0.5.0; `async def` only, awaited, the timeout is mandatory.

## Purpose

Stops a running target and waits for confirmation. Returns `operation="halt"`, `outcome`
(`stopped` or `exited`), `generation` and `stop`. After `stopped`, memory is accessible again.

## Contract and limitations

- An interrupt is sent only to a running target; an already stopped target gets no second interrupt.
  SIGINT after our interrupt is reported as `interrupt`; a breakpoint that arrives at the same time
  keeps its own reason.
- No confirmed stop within `timeout` is an ERROR `halt_timeout` with an unknown effect; there is no
  automatic retry.
- Stops the target, not the GDB server. After the scenario the runner makes a bounded halt attempt (2 s)
  and records `execution_cleanup`; this does not restore SRAM, FPB or VTOR.
- Refused in `def` (`async_required`).

## Example

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

## Avoid

```python
t.resume(sync=False)
waited = await t.wait(timeout=0.2)
await t.halt(timeout=2)              # skipped when wait raises: put halt into finally
```

## References

- [Live execution window](../LIVE_EXECUTION.md), [VTOR/FPB observer](../LIVE_OBSERVER.md).
- [API specification](../../TECHNICAL_SPECIFICATION_API.md) (Russian), items 4.22.
- [resume](resume.md), [wait](wait.md), [halt](halt.md).
