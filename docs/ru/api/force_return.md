# force_return

[API](index.md) · [English](../../en/api/force_return.md)

`force_return(expression) -> None`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §4.7 |
| API_VERSION | 1 |

## Контракт

Выполняет GDB return с expression и записывает операцию, имя функции и выражение в mutations. Пустая строка используется для void.

Возврат действует на выбранный кадр; журнал берёт имя newest_frame. Не меняйте выбранный кадр, если нужна согласованность имени. Остаток функции пропускается, уже выполненные эффекты не откатываются. Тип/ABI должны поддерживаться GDB; это не finish.

## Пример

```python
target.reach("HAL_ADC_Start_DMA")
target.force_return("(HAL_StatusTypeDef)1")
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §4.7.
- [Реализация](../../../stm32_gdbtest/target.py).
- [Сценарий или проверка реализации](../../../tests/hal-f030/profile/tests/board/test_hal_methods.py).
- [reach](reach.md), [set_value](set_value.md).
