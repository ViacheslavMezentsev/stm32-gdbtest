# breakpoint

[API](index.md) · [Русский](../../ru/api/breakpoint.md)

`breakpoint(location, temporary=False, *, condition=None, ignore_count=0) -> Point`

**Available since:** 0.1.0-rc.1 · **API 3 (0.5.0):** unchanged, no `await`; a point condition is evaluated without function calls.

## Purpose

Creates a hardware breakpoint at location. temporary makes it one-shot; condition is a GDB condition or None (when is the former name). Returns a `Point`; `is_valid()` and `delete()` are kept for 0.1/0.2 scenarios.

## Contract and limitations

Does not resume execution. A repeated request with the same parameters returns the active persistent point; a temporary point or another condition creates a new one, so a condition is never lost. Pending symbols and exhausted breakpoint_limit fail. The budget counts Target-owned points, not all GDB points; physical resources depend on MCU/backend. This is not a watchpoint.

## Example

```python
import gdb

bp = t.breakpoint("board_adc_sample", temporary=True)
try:
    gdb.execute("continue")
finally:
    if bp.is_valid():
        bp.delete()
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

This is an illustrative fragment; no separate hardware run of it is claimed.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.4.
- [Implementation](../../../stm32_gdbtest/target.py).
- [Scenario or implementation check](../../../stm32_gdbtest/target.py).
- [reach](reach.md), [clear](clear.md).
