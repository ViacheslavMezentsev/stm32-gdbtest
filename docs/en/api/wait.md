# wait

[API](index.md) · [Русский](../../ru/api/wait.md)

`await wait(*, timeout) -> dict`

**Available since:** 0.5.0 · **API 3 (0.5.0):** new in 0.5.0; `async def` only, awaited, the timeout is mandatory.

## Purpose

Passively waits for a stop or exit of the window opened by `resume(sync=False)`. Returns
`operation="wait"`, `outcome` (`stopped`, `exited` or `timeout`), `generation` and, on a stop, `stop`.

## Contract and limitations

- `timeout` is a mandatory finite positive number of host seconds (`invalid_timeout`).
- A timeout is a wait result, not a FAIL and not an MCU stop: the target keeps running.
  That is why [halt](halt.md) goes into `finally`.
- Sends no interrupt. A stop that already happened is not lost; waiting again for the same stop keeps
  the same `generation`. `exited` does not allow reading the memory of a finished target.
- A stop by a fault guard or an unexpected signal raises ApiError `fault_stop` / `signal_stop`.
- Refused in `def` (`async_required`); without `await` the next operation is refused (`unawaited_operation`).

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
await t.wait(timeout=5)              # no finally/halt: a timeout leaves the target running
time.sleep(1)                        # blocks GDB event handling
```

## References

- [Live execution window](../LIVE_EXECUTION.md), [VTOR/FPB observer](../LIVE_OBSERVER.md).
- [API specification](../../TECHNICAL_SPECIFICATION_API.md) (Russian), items 4.22.
- [resume](resume.md), [wait](wait.md), [halt](halt.md).
