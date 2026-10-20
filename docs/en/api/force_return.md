# force_return — removed in 0.4.0

[API](index.md) · [Русский](../../ru/api/force_return.md)

`force_return(expression) -> dict`

**Was available:** 0.1.0-rc.1 – 0.3.0 · **Removed:** 0.4.0 · **Replacement:** [ret(value=None)](ret.md): returns the operation result; check the return type and the selected frame.

In 0.3.0 the call warned `deprecated`; since 0.4.0 it raises `AttributeError`. The card is kept to migrate old scenarios.

## Migration

```python
t.reach("HAL_ADC_Start_DMA")
t.ret("(HAL_StatusTypeDef)1")
```

Before 0.4.0:

```python
t.force_return("(HAL_StatusTypeDef)1")
```

[API reference](index.md) · [Rename table](../API.md#030-package-numbers-migration-and-aliases)
