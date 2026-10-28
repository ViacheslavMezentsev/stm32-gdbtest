# call

[API](index.md) · [Русский](../../ru/api/call.md)

`call(function, *args, timeout=None) -> dict`; in `async def` use `await t.call(…)`

**Available since:** 0.3.0 · **API 3 (0.5.0):** in `async def` use `await t.call(…)`; the new `timeout=` parameter bounds the call; a call inside expressions of other methods is refused. [Sync/async rules](../LIVE_EXECUTION.md).

## Purpose

Calls a debugged program's function on the halted core and returns the call result.

## Contract and limitations

Arguments are passed by value: integers, finite floating-point numbers, booleans are accepted; GDB expression strings are rejected. The result describes `operation`, `function`, `arguments`, the built `expression`, `outcome`, `return_value` and `return_state` (`available` or `void`), and the call is recorded in `mutations`.

The name is a plain identifier or a qualified namespace/static name, such as
`demo::increment` or `Probe::twice`. In the 0.6.0 candidate, a qualified call requires
one symbol with callable code and DWARF. Overloads are refused before execution
(`ambiguous_function`), instance methods produce `unsupported_method`, missing
symbols/code produce `function_unavailable`. `object.method` remains `invalid_function`.
Qualified calls support integer/bool arguments and integer/bool/void returns;
arity, range and types are checked. Pointers, references, float, variadic functions,
template names and implicit ABI arguments are not supported yet.
Expression strings produce `unsupported_argument` for plain functions too.
Preflight does not prove execution safety. Resolution uses `may-call-functions off`,
then the selected linkage symbol is called; `expression` shows that symbol while
`function` retains the caller's name. There is no automatic retry.

Limitations: the call runs on the halted core and changes its state — the function's side effects
are kept; without `timeout=` the call is bounded only by the scenario timeout; pointers, floating-point numbers and
variadic arguments are outside the verified scope.

## Example

```python
result = t.call("app_step")
t.check("call returned a value", result["return_state"], "available")
```

An error inside the called function is reported as an operation failure, not as a debugger
exception.

## Timeout and async (0.5.0)

`timeout=` is host seconds; its integer part must be at least 1 and within the remaining scenario
deadline, otherwise the call is refused before it starts (`operation_timeout`). The module enables GDB
`direct-call-timeout` and `unwind-on-timeout`. An interrupted call with a dummy frame blocks further
execution (`call_incomplete`); cleanup does not restore the context and there is no retry.

```python
@case("HW_CALL")
async def checksum(t):
    await t.reach("app_loop")
    result = await t.call("app_checksum", 7, timeout=2)
    t.check("checksum(7)", result["return_value"], 22)
```

Avoid: a function call inside a `read`, `evaluate` or `write` expression or a navigation condition is
refused (`expression_call_forbidden`); call the function explicitly through `call`.

## References

- [API specification](../../TECHNICAL_SPECIFICATION_API.md), sections 4.8 and 4.23.

## Correct and incorrect: return values

```python
result = t.call("poll", 110, timeout=2)  # async def: await t.call(...)
t.check("returned", result["outcome"], "returned")
t.check("value available", result["return_state"], "available")
t.check("DONE", result["return_value"], 2)
```

Incorrect: `t.check("DONE", t.call("poll", 110), 2)` compares a dictionary to a number.
Do not repeat call merely to inspect its return: every call executes target code again.
Timeout uses host seconds; argument 110 is a logical tick in the teaching model.
An application's zero return is not ApiError: use check, not refused.
[Example with mutations and restoration](../../../tests/logical-time/README.en.md).

## A4.1 — namespace/static

```python
result = await t.call("Probe::twice", 6, timeout=2)
t.check("twice", result["return_value"], 12)
```

Omit await in def. Board-free regression: [run_cpp.py](../../../tests/renode-backend/run_cpp.py).
