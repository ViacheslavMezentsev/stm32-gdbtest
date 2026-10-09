# Справочник API сценариев

[Документация / Documentation](../index.md) · [API](../API.md) · [English](../../en/api/index.md)

Принятые публичные методы, свойства и декоратор. Текущий контракт: [ТЗ API](../../TECHNICAL_SPECIFICATION_API.md).

Версия поддержки означает наличие реализации; ревизия ТЗ — фиксацию контракта.
`API_VERSION=2` в кандидате 0.4.0 фиксирует удаление четырёх прежних методов; Python-версия ветки — 0.4.0, выпуск не опубликован. Это не номер релиза или ревизии ТЗ. База проверена по тегам
`v0.1.0-rc.1` и `v0.1.0-rc.2`; расширение — коммит `7ed6d0a` (0.2.0.dev0),
кандидат — `972af7c` (0.2.0rc1); пакет 0.3.0 — выпуск `v0.3.0`.

| Элемент | Сигнатура | Поддержка | ТЗ при введении |
| --- | --- | --- | --- |
| **Методы** — операции сценария | | | |
| [check](check.md) | `check(name, actual, expected=True)`, `check(rows) -> int` | 0.1.0rc1; сопоставители, истинность и таблица 0.3.0.dev0 (ядро) | 0.1.0; 0.3.4 |
| [within, near, one_of, matches](matchers.md) | `within(low, high)`, `near(value, tolerance)`, `one_of(*options)`, `matches(pattern)` | 0.3.0.dev0 (ядро) | 0.3.4 |
| [refused](refused.md) | `with refused(code, *, name=None, **details) as refusal` | 0.3.0.dev0 (ядро) | 0.3.6 |
| [breakpoint](breakpoint.md) | `breakpoint(location, temporary=False, *, condition=None) -> Point` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [reach](reach.md) | `reach(location, condition=None) -> dict` | 0.3.0.dev0 (ядро) | 0.2.9 (проект) |
| [clear](clear.md) | `clear() -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [record](record.md) | `record(name, data) -> None` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [records](records.md) | `records(name=None) -> list[dict]` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [ret](ret.md) | `ret(value=None) -> dict` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [read](read.md) | `read(path, *, fields=None, start=0, count=None) -> scalar \| list \| dict` | 0.3.0.dev0 (ядро) | 0.2.8 (проект) |
| [write](write.md) | `write(path, value, *, verify=True) -> dict`, `write(rows) -> list` | 0.3.0.dev0 (ядро) | 0.2.8; 0.3.6 |
| [evaluate](evaluate.md) | `evaluate(expression, *, as_type=None) -> int \| float \| bool \| str` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [registers](registers.md) | `registers(*names, frame=None) -> dict` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [frames](frames.md) | `frames(limit=16) -> dict` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [watch](watch.md) | `watch(path) -> Point` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [resume](resume.md) | `resume() -> dict` | 0.3.0.dev0 (ядро) | 0.2.9 (проект) |
| [step](step.md) | `step(count=1, *, unit="source", mode="into") -> dict` | 0.3.0.dev0 (ядро) | 0.2.9 (проект) |
| [until](until.md) | `until(location=None) -> dict` | 0.3.0.dev0 (ядро) | 0.2.9 (проект) |
| [finish](finish.md) | `finish() -> dict` | 0.3.0.dev0 (ядро) | 0.2.9 (проект) |
| [call](call.md) | `call(function, *args) -> dict` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [reset](reset.md) | `reset() -> dict` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [execute](execute.md) | `execute(command) -> str` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [symbol](symbol.md) | `symbol(name) -> dict` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [memory](memory.md) | `memory(address, size \| data, *, verify=None) -> bytes \| dict` | 0.3.0.dev0 (ядро) | 0.3.4 |
| [locals](locals.md) | `locals(frame=None) -> dict`, `arguments(frame=None) -> dict` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| **Свойства** — отображения состояния прогона | | | |
| [profile](profile.md) | `profile: Profile` | 0.1.0rc1; разделы 0.3.0.dev0 (ядро) | 0.1.0; 0.3.0 (проект) |
| **Декораторы** — объявление сценария | | | |
| [case](case.md) | `case(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [test](test.md) | `test(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.3.0 (ядро) | 0.3.0-rc.1 (проект) |
| **Классы и ошибки** — объекты, которые возвращает и поднимает API | | | |
| [RecordError](record-error.md) | `RecordError(ValueError)` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 / 0.2.1 |
| [point](point.md) | `Point: id, location, addresses, active, hit_count, condition; enable(); disable(); remove(); with` | 0.3.0.dev0 (ядро) | 0.2.9 (проект) |
| [api-error](api-error.md) | `ApiError; error.details; error.__cause__` | 0.3.0.dev0 (ядро) | 0.2.7 (проект) |
| [check-failed](check-failed.md) | `CheckFailed(name)` | 0.3.0.dev0 (ядро) | 0.2.7 (проект) |

Прежние методы удалены из кандидата 0.4.0: [value](value.md), [fields](fields.md),
[set_value](set_value.md), [force_return](force_return.md). Эти карточки оставлены только для миграции.

Пакет 0.3.0 выпущен как `v0.3.0`; действующие строки выше дополнены очисткой API для 0.4.0. Отметка «(проект)» в
столбце ТЗ называет ревизию, где метод был спроектирован, до переноса в ядро.

Target передаётся агентом; создавать его самостоятельно не нужно. GDB-вызовы выполняются
только в основном потоке GDB. boot/close/on_stop/report/owned/stops — внутренние детали.
Проектируемый пакет не вводит context/caller. Примеры требуют указанной
прошивки и места остановки; они не универсальны для всех плат.

[Techniques](../TESTING_TECHNIQUES.md) · [Configuration and migration](../API.md) · [Acceptance](../API_ACCEPTANCE.md).


## SKIP (Unreleased)

[skip(reason)](skip.md) — завершение неприменимого сценария; причина, records, код77 и миграция.
