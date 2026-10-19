# halt

[API](index.md) · [English](../../en/api/halt.md)

`await halt(*, timeout) -> dict`

Кандидат 0.5.0; API_VERSION=2; ТЗ API 0.3.22, раздел 4.22.

[Семантика, ошибки, пример и ограничения](../LIVE_EXECUTION.md).

`halt()` останавливает цель, но не завершает GDB-сервер. Штатное завершение локального OpenOCD/J-Link выполняется runner после сценария; отказ завершения даёт ERROR очистки. [Жизненный цикл](../backends/openocd.md#штатное-завершение-локального-openocdj-link).
