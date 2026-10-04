# Scenario API reference

[Документация / Documentation](../index.md) · [API](../API.md) · [Русский](../../ru/api/index.md)

Accepted public methods, properties and decorator. Current contract: [API specification 0.3.2](../../TECHNICAL_SPECIFICATION_API.md).

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
| [reach](reach.md) | `reach(location, *, condition=None) -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [set_value](set_value.md) | `set_value(expression, value) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [force_return](force_return.md) | `force_return(expression) -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [clear](clear.md) | `clear() -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [record](record.md) | `record(name, data) -> None` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [records](records.md) | `records(name=None) -> list[dict]` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [config](config.md) | `config: Mapping` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [config_props](config-props.md) | `config_props: Mapping` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [RecordError](record-error.md) | `RecordError(ValueError)` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 / 0.2.1 |
| [case](case.md) | `case(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [ret](ret.md) | `ret(value=None) -> dict` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [read](read.md) | `read(path, *, fields=None, start=0, count=None) -> scalar \| list \| dict` | 0.3.0.dev0 (core) | 0.2.8 (design) |
| [write](write.md) | `write(path, value, *, verify=True) -> dict` | 0.3.0.dev0 (core) | 0.2.8 (design) |
| [evaluate](evaluate.md) | `evaluate(expression, *, as_type=None) -> int \| float \| bool` | not released | 0.3.0 (design) |
| [registers](registers.md) | `registers(*names, frame=None) -> dict` | not released | 0.3.0 (design) |
| [frames](frames.md) | `frames(limit=16) -> dict` | not released | 0.3.0 (design) |
| [point](point.md) | `Point: id, location, addresses, active, hit_count; remove(); with` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [watch](watch.md) | `watch(path) -> Point` | not released | 0.3.0 (design) |
| [resume](resume.md) | `resume() -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [step](step.md) | `step(count=1, *, unit="source", mode="into") -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [until](until.md) | `until(location=None) -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [finish](finish.md) | `finish() -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [call](call.md) | `call(function, *args) -> dict` | 0.3.0.dev0 (core) | 0.3.1 (design) |
| [reset](reset.md) | `reset() -> dict` | not released | 0.3.0 (design) |
| [execute](execute.md) | `execute(command) -> str` | 0.3.0.dev0 (core) | 0.3.2 (design) |
| [settings](settings.md) | `settings: Mapping` | not released | 0.3.0 (design) |
| [sources](sources.md) | `sources: Mapping` | not released | 0.3.0 (design) |
| [test](test.md) | `test(identifier, *, timeout_s=20, labels=(), contracts=())` | not released | 0.3.0 (design) |
| [api-error](api-error.md) | `ApiError; error.details; error.__cause__` | 0.3.0.dev0 (core) | 0.2.7 (design) |
| [check-failed](check-failed.md) | `CheckFailed(name)` | 0.3.0.dev0 (core) | 0.2.7 (design) |

Designed 0.3.0 package (not released): methods that passed reference validation. The rows above are
not an accepted contract: it is fixed by an API specification revision when the package moves into
the core.

The agent supplies Target; do not construct it. GDB calls run only on the main GDB
thread. boot/close/on_stop/report/owned/stops are internal. The designed package introduces no context/caller.
are outside the accepted package. Examples require matching firmware and stop context;
they are not universal across boards.

[Techniques](../TESTING_TECHNIQUES.md) · [Configuration and migration](../API.md) · [Acceptance](../API_ACCEPTANCE.md).
