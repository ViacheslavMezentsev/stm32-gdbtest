# Справочник API сценариев

[Документация / Documentation](../index.md) · [API](../API.md) · [English](../../en/api/index.md)

Принятые публичные методы, свойства и декоратор. Текущий контракт: [ТЗ API 0.2.4](../../TECHNICAL_SPECIFICATION_API.md).

Версия поддержки означает наличие реализации; ревизия ТЗ — фиксацию контракта.
`API_VERSION=1` не является номером релиза или ревизии ТЗ. База проверена по тегам
`v0.1.0-rc.1` и `v0.1.0-rc.2`; расширение — коммит `7ed6d0a` (0.2.0.dev0),
кандидат — `972af7c` (0.2.0rc1). Нового опубликованного тега пока нет.

| Элемент | Сигнатура | Поддержка | ТЗ при введении |
| --- | --- | --- | --- |
| [check](check.md) | `check(name, actual, expected) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [value](value.md) | `value(expression) -> int` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [fields](fields.md) | `fields(expression, expected) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [breakpoint](breakpoint.md) | `breakpoint(function, temporary=False, when=None) -> gdb.Breakpoint` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [reach](reach.md) | `reach(function, when=None) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [set_value](set_value.md) | `set_value(expression, value) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [force_return](force_return.md) | `force_return(expression) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [clear](clear.md) | `clear() -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [record](record.md) | `record(name, data) -> None` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [records](records.md) | `records(name=None) -> list[dict]` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [config](config.md) | `config: Mapping` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [config_props](config-props.md) | `config_props: Mapping` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [RecordError](record-error.md) | `RecordError(ValueError)` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 / 0.2.1 |
| [case](case.md) | `case(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |

Target передаётся агентом; создавать его самостоятельно не нужно. GDB-вызовы выполняются
только в основном потоке GDB. boot/close/on_stop/report/owned/stops — внутренние детали.
read/context/caller/finish не входят в принятый пакет. Примеры требуют указанной
прошивки и места остановки; они не универсальны для всех плат.

[Techniques](../TESTING_TECHNIQUES.md) · [Configuration and migration](../API.md) · [Acceptance](../API_ACCEPTANCE.md).
