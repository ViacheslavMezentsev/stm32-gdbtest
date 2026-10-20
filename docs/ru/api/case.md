# case

[API](index.md) · [English](../../en/api/case.md)

`case(identifier, *, timeout_s=20, labels=(), contracts=())`

**Доступен с:** 0.1.0-rc.1 · **API 3 (0.5.0):** форма функции выбирает режим: `def` — синхронный, `async def` — с `await` для навигации, `call`, `wait` и `halt`. [Правила sync/async](../LIVE_EXECUTION.md).

## Назначение

Декоратор задаёт метаданные сценария. Верхнеуровневая функция принимает один Target; вызывается агентом после reset и остановки в main.

## Контракт и ограничения

Сборщик читает AST без выполнения сценария: параметры должны быть литералами, case без alias. ID: HW_[A-Z0-9_]+, timeout_s: целое 1..300 с; labels: [a-z0-9_-]+, contracts: [a-z][a-z0-9_]+. Импорт не требует GDB. Декоратор возвращает функцию без обёртки; некорректные метаданные отклоняются сборщиком.

## Пример

```python
from stm32_gdbtest import case

# Check the initial publication count at main.
@case("HW_EXAMPLE", timeout_s=20, labels=("adc",))
def example(t):
    t.check("initial count", t.read("board_adc_sequences"), 0)
```

Фрагмент для тела сценария (для case — целое объявление). Символы и макросы должны присутствовать в ELF; MCU остановлен в подходящем контексте.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), §5.1.
- [Реализация](../../../stm32_gdbtest/__init__.py).
- [Сценарий или проверка реализации](../../../tests/firmware/common/tests/board/test_measurements.py).
- [check](check.md), [reach](reach.md).
