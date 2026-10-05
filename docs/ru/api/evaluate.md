# evaluate

[API](index.md) · [English](../../en/api/evaluate.md)

`evaluate(expression, *, as_type=None) -> int | float | bool | str`

| Свойство | Значение |
| --- | --- |
| Поддержка в модуле | 0.3.0.dev0 (ядро) |
| Контракт принят в ТЗ API | не принят; проектируемая ревизия 0.3.0 |
| API_VERSION | 1 (действующий контракт не изменяется) |
| Основание | согласованная проверочная прошивка `tests/firmware` и её сценарии (`HW_CI_RET_RECEIVER`, `HW_CI_MEASUREMENT_SERIES`) |

## Назначение

Вычисляет выражение в контексте остановленной программы и возвращает результат заданного простого
типа.

## Контракт и ограничения

Преобразование выполняется к запрошенному типу; неподдерживаемый тип или ошибка выражения
возвращается как отказ операции.

`as_type=str` (или `"str"`) читает C-строку: массив `char[N]` — до первого нуля или до конца массива,
указатель `char *` — до нуля, не более `STRING_LIMIT = 256` байт. Байты, не являющиеся UTF-8,
заменяются символом `�`; строка без нуля в пределах лимита возвращается усечённой с отметкой
`truncated` в `report["evaluations"]`. NULL-указатель — `null_pointer`, массив не из `char` —
`unsupported_type`.

Ограничения: выражение вычисляется на текущем кадре; побочные эффекты выражения не откатываются;
вызовы функций внутри выражения не входят в проверенный объём.

## Пример

```python
t.evaluate("app_state.ticks", as_type=int)
t.evaluate("app_state.led == 1", as_type=bool)
version = t.evaluate("app_info.version", as_type=str)   # "v1.2.0-ci" из char version[16]
board = t.evaluate("app_info.board", as_type=str)       # "stm32-gdbtest-ci" из const char *
t.check("version", version, matches(r"^v1\.\d+\.\d+"))
```

Ошибка GDB при разборе или вычислении выражения сохраняется как причина отказа.

## Ссылки

- [ТЗ API / API specification](../../TECHNICAL_SPECIFICATION_API.md), ревизия 0.2.5; `as_type=str`: ревизия 0.3.5, п. 4.18.1–4.18.2.
