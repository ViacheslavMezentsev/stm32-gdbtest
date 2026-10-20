# set_value — удалён в 0.4.0

[API](index.md) · [English](../../en/api/set_value.md)

`set_value(expression, value) -> None`

**Был доступен:** 0.1.0-rc.1 – 0.3.0 · **Удалён:** 0.4.0 · **Замена:** [write(path, value)](write.md): возвращает результат и проверяет запись, если объект читается из SRAM.

В 0.3.0 вызов предупреждал `deprecated`, с 0.4.0 даёт `AttributeError`. Карточка оставлена для миграции старых сценариев.

## Миграция

```python
saved = t.read("board_adc_sequences")
try:
    t.write("board_adc_sequences", 0)
    t.check("counter injected", t.read("board_adc_sequences"), 0)
finally:
    t.write("board_adc_sequences", saved)
```

Было (до 0.4.0):

```python
t.set_value("board_adc_sequences", 0)
```

[Справочник API](index.md) · [Таблица переименований](../API.md#пакет-030-числа-миграция-и-алиасы)
