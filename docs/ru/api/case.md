# case

[API](index.md) · [English](../../en/api/case.md)

`case(identifier, *, timeout_s=20, labels=(), contracts=())`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.1.0rc1 / v0.1.0-rc.1 |
| Контракт принят в ТЗ API | 0.1.0; §5.1 |
| API_VERSION | 1 |
| Синоним нового имени | `test`; алиас действует без предупреждений до 1.0, удаление в 0.4.0 |
| Синоним прежнего имени | `test(...)`; алиас действует без предупреждений до 1.0, удаление в 0.4.0 |

## Контракт

Декоратор задаёт метаданные сценария. Верхнеуровневая функция принимает один Target; вызывается агентом после reset и остановки в main.

Сборщик читает AST без выполнения сценария: параметры должны быть литералами, case без alias. ID: HW_[A-Z0-9_]+, timeout_s: целое 1..300 с; labels: [a-z0-9_-]+, contracts: [a-z][a-z0-9_]+. Импорт не требует GDB. Декоратор возвращает функцию без обёртки; некорректные метаданные отклоняются сборщиком.

## Пример

```python
from stm32_gdbtest import case


# Check the initial publication count at main.
@case("HW_EXAMPLE", timeout_s=20, labels=("adc",))
def example(target):
    target.check("initial count", target.value("board_adc_sequences"), 0)
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §5.1.
- [Реализация](../../../stm32_gdbtest/__init__.py).
- [Сценарий или проверка реализации](../../../tests/firmware/profiles/f411ce/tests/board/test_measurements.py).
- [check](check.md), [reach](reach.md).
