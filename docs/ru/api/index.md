# Справочник API сценариев

[Документация / Documentation](../index.md) · [API](../API.md) · [English](../../en/api/index.md)

Принятые публичные методы, свойства и декоратор. Текущий контракт: [ТЗ API 0.3.0](../../TECHNICAL_SPECIFICATION_API.md).

Версия поддержки означает наличие реализации; ревизия ТЗ — фиксацию контракта.
`API_VERSION=1` не является номером релиза или ревизии ТЗ. База проверена по тегам
`v0.1.0-rc.1` и `v0.1.0-rc.2`; расширение — коммит `7ed6d0a` (0.2.0.dev0),
кандидат — `972af7c` (0.2.0rc1). Нового опубликованного тега пока нет.

| Элемент | Сигнатура | Поддержка | ТЗ при введении |
| --- | --- | --- | --- |
| **Методы** — операции сценария | | | |
| [check](check.md) | `check(name, actual, expected) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [value](value.md) | `value(expression) -> int` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [fields](fields.md) | `fields(expression, expected) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [breakpoint](breakpoint.md) | `breakpoint(function, temporary=False, when=None) -> gdb.Breakpoint` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [reach](reach.md) | `reach(location, *, condition=None) -> dict` | 0.3.0.dev0 (ядро) | 0.2.9 (проект) |
| [set_value](set_value.md) | `set_value(expression, value) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [force_return](force_return.md) | `force_return(expression) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [clear](clear.md) | `clear() -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [record](record.md) | `record(name, data) -> None` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [records](records.md) | `records(name=None) -> list[dict]` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [ret](ret.md) | `ret(value=None) -> dict` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [read](read.md) | `read(path, *, fields=None, start=0, count=None) -> scalar \| list \| dict` | 0.3.0.dev0 (ядро) | 0.2.8 (проект) |
| [write](write.md) | `write(path, value, *, verify=True) -> dict` | 0.3.0.dev0 (ядро) | 0.2.8 (проект) |
| [evaluate](evaluate.md) | `evaluate(expression, *, as_type=None) -> int \| float \| bool` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
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
| **Свойства** — отображения состояния прогона | | | |
| [config](config.md) | `config: Mapping` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [config_props](config-props.md) | `config_props: Mapping` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [settings](settings.md) | `settings: Mapping` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| [sources](sources.md) | `sources: Mapping` | 0.3.0.dev0 (ядро) | 0.3.0 (проект) |
| **Декораторы** — объявление сценария | | | |
| [case](case.md) | `case(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [test](test.md) | `test(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.3.0 (ядро) | 0.3.0-rc.1 (проект) |
| **Классы и ошибки** — объекты, которые возвращает и поднимает API | | | |
| [RecordError](record-error.md) | `RecordError(ValueError)` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 / 0.2.1 |
| [point](point.md) | `Point: id, location, addresses, active, hit_count; remove(); with` | 0.3.0.dev0 (ядро) | 0.2.9 (проект) |
| [api-error](api-error.md) | `ApiError; error.details; error.__cause__` | 0.3.0.dev0 (ядро) | 0.2.7 (проект) |
| [check-failed](check-failed.md) | `CheckFailed(name)` | 0.3.0.dev0 (ядро) | 0.2.7 (проект) |

Проектируемый пакет 0.3.0 (не выпущено): методы, прошедшие ссылочную верификацию. Строки выше не
являются принятым контрактом: контракт закрепляется ревизией ТЗ API при переносе в ядро.

Target передаётся агентом; создавать его самостоятельно не нужно. GDB-вызовы выполняются
только в основном потоке GDB. boot/close/on_stop/report/owned/stops — внутренние детали.
Проектируемый пакет не вводит context/caller. Примеры требуют указанной
прошивки и места остановки; они не универсальны для всех плат.

[Techniques](../TESTING_TECHNIQUES.md) · [Configuration and migration](../API.md) · [Acceptance](../API_ACCEPTANCE.md).
