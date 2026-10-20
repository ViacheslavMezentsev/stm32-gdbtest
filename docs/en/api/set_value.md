# set_value — removed in 0.4.0

[API](index.md) · [Русский](../../ru/api/set_value.md)

`set_value(expression, value) -> None`

**Was available:** 0.1.0-rc.1 – 0.3.0 · **Removed:** 0.4.0 · **Replacement:** [write(path, value)](write.md): returns a result and verifies the write when the object is readable in SRAM.

In 0.3.0 the call warned `deprecated`; since 0.4.0 it raises `AttributeError`. The card is kept to migrate old scenarios.

## Migration

```python
saved = t.read("board_adc_sequences")
try:
    t.write("board_adc_sequences", 0)
    t.check("counter injected", t.read("board_adc_sequences"), 0)
finally:
    t.write("board_adc_sequences", saved)
```

Before 0.4.0:

```python
t.set_value("board_adc_sequences", 0)
```

[API reference](index.md) · [Rename table](../API.md#030-package-numbers-migration-and-aliases)
