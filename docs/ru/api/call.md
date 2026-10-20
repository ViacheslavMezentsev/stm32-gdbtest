# call

[API](index.md) · [English](../../en/api/call.md)

`call(function, *args, timeout=None) -> dict`; в `async def` — `await t.call(…)`

**Доступен с:** 0.3.0 · **API 3 (0.5.0):** в `async def` — `await t.call(…)`; новый параметр `timeout=` ограничивает вызов; вызов внутри выражений других методов отклоняется. [Правила sync/async](../LIVE_EXECUTION.md).

## Назначение

Вызывает функцию отлаживаемой программы на остановленном ядре и возвращает результат вызова.

## Контракт и ограничения

Аргументы передаются по значению: принимаются целые, конечные числа с плавающей точкой, логические значения; строки-выражения GDB не принимаются. Результат описывает `operation`, `function`, `arguments`, построенное `expression`, `outcome`, `return_value` и `return_state` (`available` или `void`), а вызов записывается в `mutations`.

Имя функции должно быть простым идентификатором. `Class::method`, `namespace::function`
и `object.method` дают `invalid_function`; строковый аргумент — `unsupported_argument`.
Успешный [C++ preflight](../CONTRACTS.md) не расширяет этот интерфейс.

Ограничения: вызов выполняется на остановленном ядре и меняет его состояние — побочные эффекты
функции сохраняются; без `timeout=` вызов ограничен только таймаутом сценария; указатели, числа с плавающей
точкой и переменное число аргументов в проверенный объём не входят.

## Пример

```python
result = t.call("app_step")
t.check("call returned a value", result["return_state"], "available")
```

Ошибка внутри вызванной функции возвращается как отказ операции, а не как исключение отладчика.

## Таймаут и async (0.5.0)

`timeout=` — секунды хоста, целая часть не меньше 1 и не больше остатка срока сценария; недостаточный
бюджет отклоняется до вызова (`operation_timeout`). Модуль включает `direct-call-timeout` и
`unwind-on-timeout` GDB. Прерванный вызов с dummy frame блокирует дальнейшее продолжение
(`call_incomplete`); очистка не восстанавливает контекст, повтора нет.

```python
@case("HW_CALL")
async def checksum(t):
    await t.reach("app_loop")
    result = await t.call("app_checksum", 7, timeout=2)
    t.check("checksum(7)", result["return_value"], 22)
```

Не рекомендуется: вызов функции внутри выражения `read`, `evaluate`, `write` или условия навигации —
он отклоняется (`expression_call_forbidden`); вызывайте функцию явно через `call`.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), разделы 4.8 и 4.23.
