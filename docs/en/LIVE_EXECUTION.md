# Live execution window

[Documentation](index.md) · [API](api/index.md) · [Русский](../ru/LIVE_EXECUTION.md)

0.5.0 candidate, API_VERSION=2. Ordinary `def` scenarios and blocking `resume()` remain
supported. Live windows use `async def`: the runner resumes the coroutine on GDB's main
thread, not inside asyncio or a worker thread.

```python
from stm32_gdbtest import case


# Observe a bounded interval and read the result after confirmed stop.
@case("HW_LIVE", timeout_s=15)
async def live(t):
    t.resume(sync=False)
    try:
        window = await t.wait(timeout=0.2)
        t.record("window", window)
    finally:
        await t.halt(timeout=2.0)
    t.check("result available", t.read("counter"), 3)
```

| Operation | Result and scope |
| --- | --- |
| `resume()` / `resume(sync=True)` | Existing synchronous continuation until stop |
| `resume(sync=False)` | Async scenarios only: `started`, `generation`; does not mean the target is still running at return |
| `await wait(timeout=...)` | Passive wait: `stopped`, `exited` or `timeout`; never sends interrupt |
| `await halt(timeout=...)` | Interrupt a running target and await confirmation; no duplicate interrupt when already stopped; target exit returns `exited` |

Stop includes the reason; fault guards and unexpected signals raise ApiError `fault_stop` /
`signal_stop`. SIGINT following our interrupt is marked `interrupt`; a racing breakpoint
retains its meaning. Early stops are retained; a new resume clears the previous stop.
Repeated observation of the same stop keeps its generation. `exited` does not permit
memory access to a terminated target.

Timeout is a required finite positive number of host seconds. A wait timeout is a result,
not FAIL or MCU halt. `halt_timeout` is ERROR with unknown effect. Command errors never
trigger an automatic retry. GDB command and outer scenario timeouts still apply: the await
deadline is not a hard bound on a stalled GDB command. Connection loss does not guarantee
halt or restoration.

While running or in unknown state, read/write/memory, evaluate, MMIO, call, navigation and
execute refuse before a target request. Python data, record and checks of ready values
remain available. Direct `gdb` access is the author's responsibility and can bypass these
guards. Single inferior/thread, all-stop only; non-stop, concurrent awaits, arbitrary
asyncio awaitables and live memory reads are unsupported. Existing points/guards remain;
no new breakpoint is added to end the window.

On normal return, FAIL/ERROR/SKIP, the runner makes a bounded halt attempt (2 s), records
`execution_cleanup` separately, then performs capture/teardown. Cleanup failure produces
ERROR while preserving the previous outcome and body error. This is not SRAM/FPB/VTOR
restoration or a guarantee after killing GDB. Leave cleanup time within the scenario limit.

Do not block a coroutine with sleep or a CPU loop: that blocks GDB event processing.
Host window duration is not MCU execution time and differs from Renode virtual time.
Wait/halt use GDB's event loop; a background timer only calls thread-safe `post_event`.
All commands and coroutine continuations run on GDB's main thread.

Example and real-runner validation: [Renode fixture](../../tests/renode-backend/README.md).
Emulator results do not qualify hardware: P3 has not yet been accepted on boards.
