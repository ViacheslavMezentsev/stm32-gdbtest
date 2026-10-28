# Справочник API сценариев

[Документация / Documentation](../index.md) · [API](../API.md) · [English](../../en/api/index.md)

Методы объекта `t` (Target), декораторы и ошибки выпуска 0.6.0, API_VERSION=3. Для каждого элемента указан первый выпуск, где он доступен, и изменения API 3 (с отметкой «0.6.0» для изменений этого выпуска). Совместимые сценарии 0.3.x–0.4.x работают без правок, кроме [удалённых имён](#удалённые-имена) и [скрытых вызовов функций в выражениях](../MIGRATION_050.md).

Те же группы с примерами «правильно» и «не рекомендуется» — на [сайте справочника](https://viacheslavmezentsev.github.io/stm32-gdbtest/api/).

**API 3 кратко.** Обычный def выполняет операции по очереди. В async def навигация (reach, step, until, finish, resume, reset) и call ожидаются через await; resume(sync=False) отпускает цель, await wait/halt ждут с таймаутом. Чтение, запись, проверки и записи журнала await не требуют. Выражения не вызывают функции цели.

**Что изменилось в 0.6.0.** API_VERSION остаётся 3, новое включается явно: `call` принимает `this=`, `signature=` и аргументы `Pointer`/`Reference` для C++; `records()` по умолчанию отказывает при неполном журнале (`require_complete=True`); квоты journal/report (api schema 3) и раздельные ошибки исполнения и аудита в `resume`/`wait`/`halt` и `mmio`. Подробнее — [журналирование](../JOURNALING.md) и [переход к 0.6.0](../VERSIONING.md#переход-к-060).

## Сценарий: def и async def

Декоратор объявляет сценарий; форма функции выбирает режим исполнения.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [case](case.md) | `case(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.1.0-rc.1 | def или async def |
| [test](test.md) | `test(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.3.0 | как case |

## Навигация: reach, step, until, finish

Дойти до функции или строки, сделать шаг, выполнить до возврата. Каждая операция возвращает остановку.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [reach](reach.md) | `reach(location, condition=None) -> dict` | 0.1.0-rc.1¹ | await в async |
| [step](step.md) | `step(count=1, *, unit="source", mode="into") -> dict` | 0.3.0 | await в async |
| [until](until.md) | `until(location=None) -> dict` | 0.3.0 | await в async |
| [finish](finish.md) | `finish() -> dict` | 0.3.0 | await в async |

## Живое окно: resume, wait, halt

Отпустить цель, ждать остановки с таймаутом, остановить с подтверждением.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [resume](resume.md) | `resume(*, sync=True) -> dict` | 0.3.0 | sync=False — 0.5.0; ошибка аудита отдельно — 0.6.0 |
| [wait](wait.md) | `await wait(*, timeout) -> dict` | 0.5.0 | только async; ошибка аудита отдельно — 0.6.0 |
| [halt](halt.md) | `await halt(*, timeout) -> dict` | 0.5.0 | только async; ошибка аудита отдельно — 0.6.0 |

## Данные: read и write

Чтение объекта по имени или выражению, запись значения или таблицы записей.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [read](read.md) | `read(path, *, fields=None, start=0, count=None)` | 0.3.0 | без вызовов в выражении |
| [write](write.md) | `write(path, value, *, verify=True) -> dict; write(rows) -> list` | 0.3.0 | без вызовов в выражении |

## Выражения и память: evaluate, memory, symbol

Значение выражения нужного типа; байты SRAM/Flash по адресу символа.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [evaluate](evaluate.md) | `evaluate(expression, *, as_type=None)` | 0.3.0 | без вызовов в выражении |
| [memory](memory.md) | `memory(address, size \| data, *, verify=None)` | 0.3.0 | без изменений |
| [symbol](symbol.md) | `symbol(name) -> dict` | 0.3.0 | без изменений |

## Регистры: mmio.read и mmio.write

Один прямой запрос к регистру по имени из снимка SVD с проверкой прав и эффектов.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [mmio.read, mmio.write](mmio.md) | `mmio.read(name, *, allow_effects=False) -> int; mmio.write(name, value, *, allow_effects=False) -> dict` | 0.5.0 | новое; двойной отказ — 0.6.0 |

## Проверки: check, сопоставители, refused

Именованная проверка или таблица проверок; ожидаемый отказ API с кодом.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [check](check.md) | `check(name, actual, expected=True); check(rows) -> int` | 0.1.0-rc.1¹ | без вызовов в выражении; квоты — 0.6.0 |
| [within, near, one_of, matches](matchers.md) | `within(low, high), near(value, tolerance), one_of(*options), matches(pattern)` | 0.3.0 | без изменений |
| [refused](refused.md) | `with refused(code, *, name=None, **details) as refusal` | 0.3.0 | без изменений |

## Инъекции: ret и call

Подменить возврат текущей функции; вызвать функцию прошивки и получить результат.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [ret](ret.md) | `ret(value=None) -> dict` | 0.3.0 | без изменений |
| [call](call.md) | `call(function, *args, this=None, signature=None, timeout=None) -> dict` | 0.3.0 | await в async; timeout=; this, signature, Pointer/Reference — 0.6.0 |

## Точки: breakpoint, watch, Point, clear

Точки останова и наблюдения как объекты Point с состоянием и снятием.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [breakpoint](breakpoint.md) | `breakpoint(location, temporary=False, *, condition=None, ignore_count=0) -> Point` | 0.1.0-rc.1 | без изменений |
| [watch](watch.md) | `watch(path) -> Point` | 0.3.0 | без изменений |
| [Point](point.md) | `Point: active, hit_count, condition; enable(), disable(), remove(), with` | 0.3.0 | без изменений |
| [clear](clear.md) | `clear() -> None` | 0.1.0-rc.1 | без изменений |

## Журнал и SKIP: record, records, skip

Произвольные данные в отчёт; выборка своих записей; завершение неприменимого сценария.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [record](record.md) | `record(name, data) -> None` | 0.3.0 | квоты journal — 0.6.0 |
| [records](records.md) | `records(name=None, *, require_complete=True) -> list[dict]` | 0.3.0 | require_complete — 0.6.0 |
| [skip](skip.md) | `skip(reason) -> NoReturn` | 0.4.0 | без изменений |

## Контекст: profile, registers, frames, locals

Данные прогона и проекта; регистры ядра, стек вызовов, локальные переменные и аргументы.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [profile](profile.md) | `profile: Profile` | 0.1.0-rc.1¹ | без изменений |
| [registers](registers.md) | `registers(*names, frame=None) -> dict` | 0.3.0 | без изменений |
| [frames](frames.md) | `frames(limit=16) -> dict` | 0.3.0 | без изменений |
| [locals, arguments](locals.md) | `locals(frame=None) -> dict; arguments(frame=None) -> dict` | 0.3.0 | без изменений |

## Сброс и команды GDB: reset, execute

Сброс цели с остановкой; произвольная команда GDB как низкоуровневый выход.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [reset](reset.md) | `reset() -> dict` | 0.3.0 | await в async |
| [execute](execute.md) | `execute(command) -> str` | 0.3.0 | отклоняется в async |

## Ошибки: ApiError, CheckFailed, RecordError

Отказ операции с кодом, стадией и эффектом; проваленная проверка; ошибка журнала.

| Элемент | Сигнатура | Доступен с | API 3 |
| --- | --- | --- | --- |
| [ApiError](api-error.md) | `ApiError: details, code, __cause__` | 0.3.0 | новые коды |
| [CheckFailed](check-failed.md) | `CheckFailed(ApiError, AssertionError)` | 0.1.0-rc.1¹ | без изменений |
| [RecordError](record-error.md) | `RecordError(ValueError)` | 0.3.0 | incomplete_evidence, лимиты — 0.6.0 |

¹ Базовая форма; расширения указаны в карточке (ожидание и `condition` у reach, сопоставители и таблица у check, разделы profile, публичный импорт CheckFailed — 0.3.0).

## Удалённые имена

Были доступны с 0.1.0-rc.1 по 0.3.0 (в 0.3.0 с предупреждением `deprecated`), удалены в 0.4.0.

| Имя | Замена |
| --- | --- |
| [value](value.md) | `read, evaluate` |
| [fields](fields.md) | `read(path, fields=…), check(rows)` |
| [set_value](set_value.md) | `write` |
| [force_return](force_return.md) | `ret` |

Target передаётся агентом; создавать его не нужно. Вызовы GDB выполняются только в основном потоке GDB; `boot`, `close`, `on_stop`, `report`, `owned`, `stops` — внутренние детали. Примеры требуют указанной прошивки и места остановки.

Связанные страницы: [каталог техник](../TESTING_TECHNIQUES.md) · [конфигурация и миграция](../API.md) · [живое окно](../LIVE_EXECUTION.md) · [регистры MMIO](../MMIO.md) и [SVD](../SVD.md) · [переход на 0.5.0](../MIGRATION_050.md) · [приёмка](../API_ACCEPTANCE.md) · [ТЗ API](../../TECHNICAL_SPECIFICATION_API.md). Офлайн-проверка связей — [CLI inspect](../HIL_INSPECT.md), не метод Target.
