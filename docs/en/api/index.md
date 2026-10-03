# Scenario API reference

[Документация / Documentation](../index.md) · [API](../API.md) · [Русский](../../ru/api/index.md)

Accepted public methods, properties and decorator. Current contract: [API specification 0.2.4](../../TECHNICAL_SPECIFICATION_API.md).

Support version identifies implementation availability; specification revision identifies
contract adoption. API_VERSION=1 is neither a release nor a specification revision.
The baseline was checked against v0.1.0-rc.1 and v0.1.0-rc.2; extension commit
7ed6d0a is 0.2.0.dev0; candidate 972af7c is 0.2.0rc1. No new published tag exists yet.

| Entry | Signature | Support | Initial specification |
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

The agent supplies Target; do not construct it. GDB calls run only on the main GDB
thread. boot/close/on_stop/report/owned/stops are internal. read/context/caller/finish
are outside the accepted package. Examples require matching firmware and stop context;
they are not universal across boards.

[Techniques](../TESTING_TECHNIQUES.md) · [Configuration and migration](../API.md) · [Acceptance](../API_ACCEPTANCE.md).
