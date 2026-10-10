# Scenario API reference

[Документация / Documentation](../index.md) · [API](../API.md) · [Русский](../../ru/api/index.md)

Accepted public methods, properties and decorator. Current contract: [API specification](../../TECHNICAL_SPECIFICATION_API.md).

Support version identifies implementation availability; specification revision identifies
contract adoption. API_VERSION=2 in the 0.4.0 candidate records removal of four former methods; the branch's package version is 0.4.0, but the release is unpublished. API_VERSION is neither a release nor a specification revision.
The baseline was checked against v0.1.0-rc.1 and v0.1.0-rc.2; extension commit
7ed6d0a is 0.2.0.dev0; candidate 972af7c is 0.2.0rc1; the 0.3.0 package is release `v0.3.0`.

| Entry | Signature | Support | Initial specification |
| --- | --- | --- | --- |
| **Methods** — scenario operations | | | |
| [check](check.md) | `check(name, actual, expected=True)`, `check(rows) -> int` | 0.1.0rc1; matchers, truth and table 0.3.0.dev0 (core) | 0.1.0; 0.3.4 |
| [within, near, one_of, matches](matchers.md) | `within(low, high)`, `near(value, tolerance)`, `one_of(*options)`, `matches(pattern)` | 0.3.0.dev0 (core) | 0.3.4 |
| [refused](refused.md) | `with refused(code, *, name=None, **details) as refusal` | 0.3.0.dev0 (core) | 0.3.6 |
| [breakpoint](breakpoint.md) | `breakpoint(location, temporary=False, *, condition=None) -> Point` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [reach](reach.md) | `reach(location, condition=None) -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [clear](clear.md) | `clear() -> None` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [record](record.md) | `record(name, data) -> None` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [records](records.md) | `records(name=None) -> list[dict]` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 |
| [ret](ret.md) | `ret(value=None) -> dict` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [read](read.md) | `read(path, *, fields=None, start=0, count=None) -> scalar \| list \| dict` | 0.3.0.dev0 (core) | 0.2.8 (design) |
| [write](write.md) | `write(path, value, *, verify=True) -> dict`, `write(rows) -> list` | 0.3.0.dev0 (core) | 0.2.8; 0.3.6 |
| [evaluate](evaluate.md) | `evaluate(expression, *, as_type=None) -> int \| float \| bool \| str` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [registers](registers.md) | `registers(*names, frame=None) -> dict` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [frames](frames.md) | `frames(limit=16) -> dict` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [watch](watch.md) | `watch(path) -> Point` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [resume](resume.md) | `resume() -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [step](step.md) | `step(count=1, *, unit="source", mode="into") -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [until](until.md) | `until(location=None) -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [finish](finish.md) | `finish() -> dict` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [call](call.md) | `call(function, *args) -> dict` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [reset](reset.md) | `reset() -> dict` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [execute](execute.md) | `execute(command) -> str` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [symbol](symbol.md) | `symbol(name) -> dict` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| [memory](memory.md) | `memory(address, size \| data, *, verify=None) -> bytes \| dict` | 0.3.0.dev0 (core) | 0.3.4 |
| [locals](locals.md) | `locals(frame=None) -> dict`, `arguments(frame=None) -> dict` | 0.3.0.dev0 (core) | 0.3.0 (design) |
| **Properties** — run state mappings | | | |
| [profile](profile.md) | `profile: Profile` | 0.1.0rc1; sections 0.3.0.dev0 (core) | 0.1.0; 0.3.0 (design) |
| **Decorators** — scenario declaration | | | |
| [case](case.md) | `case(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.1.0rc1 / v0.1.0-rc.1 | 0.1.0 |
| [test](test.md) | `test(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.3.0 (core) | 0.3.0-rc.1 (design) |
| **Classes and errors** — objects the API returns and raises | | | |
| [RecordError](record-error.md) | `RecordError(ValueError)` | 0.2.0.dev0 → 0.2.0rc1 | 0.2.0 / 0.2.1 |
| [point](point.md) | `Point: id, location, addresses, active, hit_count, condition; enable(); disable(); remove(); with` | 0.3.0.dev0 (core) | 0.2.9 (design) |
| [api-error](api-error.md) | `ApiError; error.details; error.__cause__` | 0.3.0.dev0 (core) | 0.2.7 (design) |
| [check-failed](check-failed.md) | `CheckFailed(name)` | 0.3.0.dev0 (core) | 0.2.7 (design) |

The former methods have been removed from the 0.4.0 candidate: [value](value.md), [fields](fields.md),
[set_value](set_value.md), [force_return](force_return.md). Their cards remain only for migration.

The 0.3.0 package is released as `v0.3.0`; the active rows above include the 0.4.0 API cleanup.
"(design)" in the specification column names the revision where a method was designed, before it
moved into the core.

The agent supplies Target; do not construct it. GDB calls run only on the main GDB
thread. boot/close/on_stop/report/owned/stops are internal. The package introduces no context/caller.
Examples require matching firmware and stop context;
they are not universal across boards.

[Techniques](../TESTING_TECHNIQUES.md) · [Configuration and migration](../API.md) · [Acceptance](../API_ACCEPTANCE.md).


## SKIP (Unreleased)

[skip(reason)](skip.md) — inapplicable scenario completion; reason, records, code77 and migration.
