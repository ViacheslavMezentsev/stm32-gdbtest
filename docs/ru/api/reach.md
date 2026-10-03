# reach

[API](index.md) · [English](../../en/api/reach.md)

`reach(function, when=None) -> None`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §4.5 |
| API_VERSION | 1 |

## Контракт

Ставит временную аппаратную точку, один раз выполняет continue и проверяет номер точки, имя кадра и условие when, если оно задано.

Посторонняя остановка не пропускается автоматически. Имя кадра сравнивается без clone, параметров и const/volatile. Точка удаляется при любом исходе. Внутреннего аргумента timeout нет: действует timeout сценария.

## Пример

```python
target.reach("board_adc_sample")
target.reach("board_delay_ms")
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.5.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py).
- [breakpoint](breakpoint.md), [case](case.md).
