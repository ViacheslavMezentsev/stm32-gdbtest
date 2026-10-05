# clear

[API](index.md) · [English](../../en/api/clear.md)

`clear() -> None`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §4.8 |
| API_VERSION | 1 |
| Основание | действующий контракт 0.1.0/0.2.0 и сценарии проверочной прошивки `tests/firmware` |

## Назначение

Удаляет все ещё действующие точки, которыми владеет Target, и очищает список владения.

## Контракт и ограничения

Удаляет также fault guards, установленные агентом. Чужие точки GDB не затрагивает. Не сбрасывает MCU и не очищает record/records. Используйте только при осознанной смене стратегии остановок.

## Пример

```python
# Deliberately remove all Target stops, including fault guards.
target.clear()
target.reach("board_adc_sample")
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

Это учебный фрагмент; отдельный аппаратный сценарий с ним не заявляется.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.8.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../stm32_gdbtest/target.py).
- [breakpoint](breakpoint.md), [reach](reach.md), [records](records.md).
