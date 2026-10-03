# breakpoint

[API](index.md) · [English](../../en/api/breakpoint.md)

`breakpoint(function, temporary=False, when=None) -> gdb.Breakpoint`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §4.4 |
| API_VERSION | 1 |

## Контракт

Создаёт аппаратную точку по строке function. temporary задаёт однократность; when — условие GDB или None. Возвращает объект GDB.

Не продолжает исполнение. Pending-символ и исчерпанный breakpoint_limit дают ошибку. Бюджет учитывает точки Target, не все точки GDB; реальные ресурсы зависят от MCU/backend. Это не watchpoint.

## Пример

```python
import gdb

bp = target.breakpoint("board_adc_sample", temporary=True)
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
