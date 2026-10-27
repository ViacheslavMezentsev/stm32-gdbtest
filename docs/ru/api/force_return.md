# force_return — удалён в 0.4.0

[API](index.md) · [English](../../en/api/force_return.md)

`force_return(expression) -> dict`

**Был доступен:** 0.1.0-rc.1 – 0.3.0 · **Удалён:** 0.4.0 · **Замена:** [ret(value=None)](ret.md): возвращает результат операции; проверьте тип возврата и выбранный кадр.

В 0.3.0 вызов предупреждал `deprecated`, с 0.4.0 даёт `AttributeError`. Карточка оставлена для миграции старых сценариев.

## Миграция

```python
t.reach("HAL_ADC_Start_DMA")
t.ret("(HAL_StatusTypeDef)1")
```

Было (до 0.4.0):

```python
t.force_return("(HAL_StatusTypeDef)1")
```

[Справочник API](index.md) · [Таблица переименований](../RELEASE_CHANGES.md)
