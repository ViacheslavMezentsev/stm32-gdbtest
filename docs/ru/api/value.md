# value — удалён в 0.4.0

[API](index.md) · [English](../../en/api/value.md)

`value(expression) -> int`

**Был доступен:** 0.1.0-rc.1 – 0.3.0 · **Удалён:** 0.4.0 · **Замена:** [read](read.md) для объекта, [evaluate](evaluate.md) для выражения; проверьте нужный тип результата.

В 0.3.0 вызов предупреждал `deprecated`, с 0.4.0 даёт `AttributeError`. Карточка оставлена для миграции старых сценариев.

## Миграция

```python
sequence = t.read("board_adc_sequences")
t.check("nonnegative sequence", sequence >= 0, True)
```

Было (до 0.4.0):

```python
t.check("nonnegative sequence", t.value("board_adc_sequences") >= 0, True)
```

[Справочник API](index.md) · [Таблица переименований](../RELEASE_CHANGES.md)
