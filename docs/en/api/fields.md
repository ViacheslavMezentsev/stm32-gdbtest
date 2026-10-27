# fields — removed in 0.4.0

[API](index.md) · [Русский](../../ru/api/fields.md)

`fields(expression, expected) -> None`

**Was available:** 0.1.0-rc.1 – 0.3.0 · **Removed:** 0.4.0 · **Replacement:** [check(rows)](check.md) to compare fields, [read(path, fields=…)](read.md) only to read them.

In 0.3.0 the call warned `deprecated`; since 0.4.0 it raises `AttributeError`. The card is kept to migrate old scenarios.

## Migration

```python
t.reach("HAL_GPIO_Init")
t.check([
    ("GPIO pin", "GPIO_Init->Pin", 1 << 5),
    ("GPIO mode", "GPIO_Init->Mode", "GPIO_MODE_OUTPUT_PP"),
])
```

Before 0.4.0:

```python
t.fields("*GPIO_Init", {"Pin": 1 << 5, "Mode": "GPIO_MODE_OUTPUT_PP"})
```

[API reference](index.md) · [Rename table](../RELEASE_CHANGES.md)
