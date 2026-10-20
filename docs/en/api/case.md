# case

[API](index.md) · [Русский](../../ru/api/case.md)

`case(identifier, *, timeout_s=20, labels=(), contracts=())`

**Available since:** 0.1.0-rc.1 · **API 3 (0.5.0):** the function form selects the mode: `def` is synchronous, `async def` awaits navigation, `call`, `wait` and `halt`. [Sync/async rules](../LIVE_EXECUTION.md).

## Purpose

Decorator declares scenario metadata. A top-level function accepts one Target and is invoked after reset and stopping at main.

## Contract and limitations

Collection reads AST without executing scenarios: arguments must be literals and case must not be aliased. ID: HW_[A-Z0-9_]+; timeout_s: integer 1..300 seconds; labels: [a-z0-9_-]+; contracts: [a-z][a-z0-9_]+. Import needs no GDB. Returns the function unchanged; the collector rejects invalid metadata.

## Example

```python
from stm32_gdbtest import case

# Check the initial publication count at main.
@case("HW_EXAMPLE", timeout_s=20, labels=("adc",))
def example(t):
    t.check("initial count", t.read("board_adc_sequences"), 0)
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §5.1.
- [Implementation](../../../stm32_gdbtest/__init__.py).
- [Scenario or implementation check](../../../tests/firmware/common/tests/board/test_measurements.py).
- [check](check.md), [reach](reach.md).
