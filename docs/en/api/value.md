# value — removed in 0.4.0

[API](index.md) · [Русский](../../ru/api/value.md)

`value(expression) -> int`

**Was available:** 0.1.0-rc.1 – 0.3.0 · **Removed:** 0.4.0 · **Replacement:** [read](read.md) for an object, [evaluate](evaluate.md) for an expression; check the required result type.

In 0.3.0 the call warned `deprecated`; since 0.4.0 it raises `AttributeError`. The card is kept to migrate old scenarios.

## Migration

```python
sequence = t.read("board_adc_sequences")
t.check("nonnegative sequence", sequence >= 0, True)
```

Before 0.4.0:

```python
t.check("nonnegative sequence", t.value("board_adc_sequences") >= 0, True)
```

[API reference](index.md) · [Rename table](../RELEASE_CHANGES.md)
