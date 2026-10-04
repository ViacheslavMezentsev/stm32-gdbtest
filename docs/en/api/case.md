# case

[API](index.md) · [Русский](../../ru/api/case.md)

`case(identifier, *, timeout_s=20, labels=(), contracts=())`

| Property | Value |
| --- | --- |
| Module support | 0.1.0rc1 / v0.1.0-rc.1 |
| Contract in API specification | 0.1.0; §5.1 |
| API_VERSION | 1 |
| Alias of the new name | `test`; the alias works without warnings until 1.0, removal in 0.4.0 |
| Former-name alias | `test(...)`; the alias works without warnings until 1.0, removal in 0.4.0 |

## Contract

Decorator declares scenario metadata. A top-level function accepts one Target and is invoked after reset and stopping at main.

Collection reads AST without executing scenarios: arguments must be literals and case must not be aliased. ID: HW_[A-Z0-9_]+; timeout_s: integer 1..300 seconds; labels: [a-z0-9_-]+; contracts: [a-z][a-z0-9_]+. Import needs no GDB. Returns the function unchanged; the collector rejects invalid metadata.

## Example

```python
from stm32_gdbtest import case


# Check the initial publication count at main.
@case("HW_EXAMPLE", timeout_s=20, labels=("adc",))
def example(target):
    target.check("initial count", target.value("board_adc_sequences"), 0)
```

Scenario-body fragment (case shows a complete declaration). Symbols/macros must exist in the ELF and the MCU must be stopped in the appropriate context.

## References

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §5.1.
- [Implementation](../../../stm32_gdbtest/__init__.py).
- [Scenario or implementation check](../../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py).
- [check](check.md), [reach](reach.md).
