# fields — удалён в 0.4.0

[API](index.md) · [English](../../en/api/fields.md)

`fields(expression, expected) -> None`

**Был доступен:** 0.1.0-rc.1 – 0.3.0 · **Удалён:** 0.4.0 · **Замена:** [check(rows)](check.md) для сравнения полей, [read(path, fields=…)](read.md) — только для чтения.

В 0.3.0 вызов предупреждал `deprecated`, с 0.4.0 даёт `AttributeError`. Карточка оставлена для миграции старых сценариев.

## Миграция

```python
t.reach("HAL_GPIO_Init")
t.check([
    ("GPIO pin", "GPIO_Init->Pin", 1 << 5),
    ("GPIO mode", "GPIO_Init->Mode", "GPIO_MODE_OUTPUT_PP"),
])
```

Было (до 0.4.0):

```python
t.fields("*GPIO_Init", {"Pin": 1 << 5, "Mode": "GPIO_MODE_OUTPUT_PP"})
```

[Справочник API](index.md) · [Таблица переименований](../RELEASE_CHANGES.md)
