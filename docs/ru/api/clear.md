# clear

[API](index.md) · [English](../../en/api/clear.md)

`clear() -> None`

**Доступен с:** 0.1.0-rc.1 · **API 3 (0.5.0):** без изменений, `await` не нужен.

## Назначение

Удаляет все ещё действующие точки, которыми владеет Target, и очищает список владения.

## Контракт и ограничения

Удаляет также fault guards, установленные агентом. Чужие точки GDB не затрагивает. Не сбрасывает MCU и не очищает record/records. Используйте только при осознанной смене стратегии остановок.

## Пример

```python
# Deliberately remove all Target stops, including fault guards.
t.clear()
t.reach("board_adc_sample")
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

Это учебный фрагмент; отдельный аппаратный сценарий с ним не заявляется.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.8.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../stm32_gdbtest/target.py).
- [breakpoint](breakpoint.md), [reach](reach.md), [records](records.md).
