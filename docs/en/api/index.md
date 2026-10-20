# Scenario API reference

[Документация / Documentation](../index.md) · [API](../API.md) · [Русский](../../ru/api/index.md)

Methods of the `t` object (Target), decorators and errors of release 0.5.0, API_VERSION=3. Each entry gives the first release where it is available and the API 3 changes. Compatible 0.3.x–0.4.x scenarios run unchanged, except for [removed names](#removed-names) and [hidden function calls in expressions](../MIGRATION_050.md).

The same groups with "recommended" and "avoid" examples are on the [reference site](https://viacheslavmezentsev.github.io/stm32-gdbtest/api/index.en.html).

**API 3 in short.** An ordinary def runs operations in order. In async def, navigation (reach, step, until, finish, resume, reset) and call are awaited; resume(sync=False) lets the target go and await wait/halt wait with a timeout. Reads, writes, checks and journal records need no await. Expressions never call target functions.

## Scenario: def and async def

The decorator declares a scenario; the function form selects the execution mode.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [case](case.md) | `case(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.1.0-rc.1 | def or async def |
| [test](test.md) | `test(identifier, *, timeout_s=20, labels=(), contracts=())` | 0.3.0 | as case |

## Navigation: reach, step, until, finish

Run to a function or line, step, run until return. Each operation returns the stop.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [reach](reach.md) | `reach(location, condition=None) -> dict` | 0.1.0-rc.1¹ | await in async |
| [step](step.md) | `step(count=1, *, unit="source", mode="into") -> dict` | 0.3.0 | await in async |
| [until](until.md) | `until(location=None) -> dict` | 0.3.0 | await in async |
| [finish](finish.md) | `finish() -> dict` | 0.3.0 | await in async |

## Live window: resume, wait, halt

Let the target run, wait for a stop with a timeout, halt with confirmation.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [resume](resume.md) | `resume(*, sync=True) -> dict` | 0.3.0 | sync=False — 0.5.0 |
| [wait](wait.md) | `await wait(*, timeout) -> dict` | 0.5.0 | async only |
| [halt](halt.md) | `await halt(*, timeout) -> dict` | 0.5.0 | async only |

## Data: read and write

Read an object by name or expression, write a value or a table of writes.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [read](read.md) | `read(path, *, fields=None, start=0, count=None)` | 0.3.0 | no calls in expressions |
| [write](write.md) | `write(path, value, *, verify=True) -> dict; write(rows) -> list` | 0.3.0 | no calls in expressions |

## Expressions and memory: evaluate, memory, symbol

An expression value of the required type; SRAM/Flash bytes at a symbol address.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [evaluate](evaluate.md) | `evaluate(expression, *, as_type=None)` | 0.3.0 | no calls in expressions |
| [memory](memory.md) | `memory(address, size \| data, *, verify=None)` | 0.3.0 | unchanged |
| [symbol](symbol.md) | `symbol(name) -> dict` | 0.3.0 | unchanged |

## Registers: mmio.read and mmio.write

One direct request to a register named in the SVD snapshot, with access-right and effect checks.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [mmio.read, mmio.write](mmio.md) | `mmio.read(name, *, allow_effects=False) -> int; mmio.write(name, value, *, allow_effects=False) -> dict` | 0.5.0 | new |

## Checks: check, matchers, refused

A named check or a table of checks; an expected API refusal with its code.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [check](check.md) | `check(name, actual, expected=True); check(rows) -> int` | 0.1.0-rc.1¹ | no calls in expressions |
| [within, near, one_of, matches](matchers.md) | `within(low, high), near(value, tolerance), one_of(*options), matches(pattern)` | 0.3.0 | unchanged |
| [refused](refused.md) | `with refused(code, *, name=None, **details) as refusal` | 0.3.0 | unchanged |

## Injection: ret and call

Replace the return of the current function; call a firmware function and get its result.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [ret](ret.md) | `ret(value=None) -> dict` | 0.3.0 | unchanged |
| [call](call.md) | `call(function, *args, timeout=None) -> dict` | 0.3.0 | await in async; timeout= |

## Points: breakpoint, watch, Point, clear

Breakpoints and watchpoints as Point objects with state and removal.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [breakpoint](breakpoint.md) | `breakpoint(location, temporary=False, *, condition=None, ignore_count=0) -> Point` | 0.1.0-rc.1 | unchanged |
| [watch](watch.md) | `watch(path) -> Point` | 0.3.0 | unchanged |
| [Point](point.md) | `Point: active, hit_count, condition; enable(), disable(), remove(), with` | 0.3.0 | unchanged |
| [clear](clear.md) | `clear() -> None` | 0.1.0-rc.1 | unchanged |

## Journal and SKIP: record, records, skip

Arbitrary data into the report; selecting your records; ending a non-applicable scenario.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [record](record.md) | `record(name, data) -> None` | 0.3.0 | unchanged |
| [records](records.md) | `records(name=None) -> list[dict]` | 0.3.0 | unchanged |
| [skip](skip.md) | `skip(reason) -> NoReturn` | 0.4.0 | unchanged |

## Context: profile, registers, frames, locals

Run and project data; core registers, call stack, locals and arguments.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [profile](profile.md) | `profile: Profile` | 0.1.0-rc.1¹ | unchanged |
| [registers](registers.md) | `registers(*names, frame=None) -> dict` | 0.3.0 | unchanged |
| [frames](frames.md) | `frames(limit=16) -> dict` | 0.3.0 | unchanged |
| [locals, arguments](locals.md) | `locals(frame=None) -> dict; arguments(frame=None) -> dict` | 0.3.0 | unchanged |

## Reset and GDB commands: reset, execute

Reset the target with a halt; an arbitrary GDB command as a low-level escape.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [reset](reset.md) | `reset() -> dict` | 0.3.0 | await in async |
| [execute](execute.md) | `execute(command) -> str` | 0.3.0 | refused in async |

## Errors: ApiError, CheckFailed, RecordError

An operation refusal with code, stage and effect; a failed check; a journal error.

| Entry | Signature | Available since | API 3 |
| --- | --- | --- | --- |
| [ApiError](api-error.md) | `ApiError: details, code, __cause__` | 0.3.0 | new codes |
| [CheckFailed](check-failed.md) | `CheckFailed(ApiError, AssertionError)` | 0.1.0-rc.1¹ | unchanged |
| [RecordError](record-error.md) | `RecordError(ValueError)` | 0.3.0 | unchanged |

¹ Base form; extensions are given in the card (reach waiting and `condition`, check matchers and table, profile sections, public CheckFailed import — 0.3.0).

## Removed names

Available from 0.1.0-rc.1 to 0.3.0 (with a `deprecated` warning in 0.3.0), removed in 0.4.0.

| Name | Replacement |
| --- | --- |
| [value](value.md) | `read, evaluate` |
| [fields](fields.md) | `read(path, fields=…), check(rows)` |
| [set_value](set_value.md) | `write` |
| [force_return](force_return.md) | `ret` |

Target is passed by the agent; do not create it. GDB calls run only on the main GDB thread; `boot`, `close`, `on_stop`, `report`, `owned`, `stops` are internal details. Examples need the named firmware and stop location.

Related pages: [technique catalogue](../TESTING_TECHNIQUES.md) · [configuration and migration](../API.md) · [live window](../LIVE_EXECUTION.md) · [MMIO registers](../MMIO.md) and [SVD](../SVD.md) · [moving to 0.5.0](../MIGRATION_050.md) · [acceptance](../API_ACCEPTANCE.md) · [API specification](../../TECHNICAL_SPECIFICATION_API.md) (Russian). Offline link checks: [CLI inspect](../HIL_INSPECT.md), not a Target method.
