# halt

[API](index.md) · [Русский](../../ru/api/halt.md)

`await halt(*, timeout) -> dict`

0.5.0 candidate; API_VERSION=2; API specification 0.3.22, section 4.22.

[Semantics, errors, example and limitations](../LIVE_EXECUTION.md).

`halt()` stops the target, not the GDB server. The runner performs graceful local OpenOCD/J-Link shutdown after the scenario; shutdown failure is a cleanup ERROR. [Lifecycle](../backends/openocd.md#graceful-local-openocdj-link-shutdown).
