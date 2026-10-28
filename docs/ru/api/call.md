# call

[API](index.md) · [English](../../en/api/call.md)

`call(function, *args, timeout=None) -> dict`; в `async def` — `await t.call(…)`

**Доступен с:** 0.3.0 · **API 3 (0.5.0):** в `async def` — `await t.call(…)`; новый параметр `timeout=` ограничивает вызов; вызов внутри выражений других методов отклоняется. [Правила sync/async](../LIVE_EXECUTION.md).

## Назначение

Вызывает функцию отлаживаемой программы на остановленном ядре и возвращает результат вызова.

## Контракт и ограничения

Аргументы передаются по значению: принимаются целые, конечные числа с плавающей точкой, логические значения; строки-выражения GDB не принимаются. Результат описывает `operation`, `function`, `arguments`, построенное `expression`, `outcome`, `return_value` и `return_state` (`available` или `void`), а вызов записывается в `mutations`.

Имя — простой идентификатор либо квалифицированное имя namespace/static, например
`demo::increment` или `Probe::twice`. В кандидате 0.6.0 квалифицированный вызов требует
единственного символа с вызываемым кодом и DWARF. Перегрузки отклоняются до исполнения
(`ambiguous_function`), нестатический метод — `unsupported_method`, отсутствующий
символ/код — `function_unavailable`. `object.method` остаётся `invalid_function`.
Для квалифицированного вызова поддержаны целые/bool и результат целое/bool/void;
проверяются число аргументов, диапазон и типы. Указатели, ссылки, float, variadic,
шаблонные имена и скрытые ABI-аргументы пока отклоняются.
Строки-выражения дают `unsupported_argument` также для обычной функции.
Preflight не доказывает безопасность исполнения. Квалифицированный вызов разрешается
при `may-call-functions off`, затем исполняется выбранный linkage-символ; его имя видно
в `expression`, а `function` сохраняет имя сценариста. Автоматического повтора нет.

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

## Правильно и неправильно: возвращаемое значение

```python
result = t.call("poll", 110, timeout=2)  # async def: await t.call(...)
t.check("returned", result["outcome"], "returned")
t.check("value available", result["return_state"], "available")
t.check("DONE", result["return_value"], 2)
```

Неправильно: `t.check("DONE", t.call("poll", 110), 2)` сравнивает словарь с числом.
Не повторяйте call ради проверки значения: каждый вызов заново исполняет код цели.
`timeout` измеряется в секундах хоста; аргумент 110 — логические тики учебной модели.
Возврат 0 прикладной функции — не ApiError: применяйте check, а не refused.
[Пример с дефектами и восстановлением](../../../tests/logical-time/README.md).

## A4.1 — namespace/static

```python
result = await t.call("Probe::twice", 6, timeout=2)
t.check("twice", result["return_value"], 12)
```

В def уберите await. Пример проверяется без платы: [run_cpp.py](../../../tests/renode-backend/run_cpp.py).
