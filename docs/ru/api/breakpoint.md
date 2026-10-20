# breakpoint

[API](index.md) · [English](../../en/api/breakpoint.md)

`breakpoint(location, temporary=False, *, condition=None, ignore_count=0) -> Point`

**Доступен с:** 0.1.0-rc.1 · **API 3 (0.5.0):** без изменений, `await` не нужен; условие точки вычисляется без вызовов функций.

## Назначение

Создаёт аппаратную точку по строке location. temporary задаёт однократность; condition — условие GDB или None (when — прежнее имя). Возвращает `Point`; методы `is_valid()` и `delete()` сохранены для сценариев 0.1/0.2.

## Контракт и ограничения

Не продолжает исполнение. Повторный запрос с теми же параметрами возвращает уже действующую постоянную точку; временная точка или другое условие создают новую, условие не теряется. Pending-символ и исчерпанный breakpoint_limit дают ошибку. Бюджет учитывает точки Target, не все точки GDB; реальные ресурсы зависят от MCU/backend. Это не watchpoint.

## Пример

```python
import gdb

bp = t.breakpoint("board_adc_sample", temporary=True)
try:
    gdb.execute("continue")
finally:
    if bp.is_valid():
        bp.delete()
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

Это учебный фрагмент; отдельный аппаратный сценарий с ним не заявляется.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.4.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../stm32_gdbtest/target.py).
- [reach](reach.md), [clear](clear.md).
