# call

[API](index.md) · [Русский](../../ru/api/call.md)

`call(function, *args, this=None, signature=None, timeout=None) -> dict`; in `async def` use `await t.call(…)`

**Available since:** 0.3.0 · **API 3 (0.5.0):** in `async def` use `await t.call(…)`; the new `timeout=` parameter bounds the call; a call inside expressions of other methods is refused. [Sync/async rules](../LIVE_EXECUTION.md).

## Purpose

Calls a debugged program's function on the halted core and returns the call result.

## Contract and limitations

Arguments are passed by value: integers, finite floating-point numbers, booleans are accepted; GDB expression strings are rejected. The result describes `operation`, `function`, `arguments`, the built `expression`, `outcome`, `return_value` and `return_state` (`available` or `void`), and the call is recorded in `mutations`.

`call(function, *args, this=None, signature=None, timeout=None)` supports an explicit
object and exact overload selection in the 0.6.0 candidate. Use await in async def.
`this="&probe"` takes the address of a named object; `this="probe_ptr"` uses a named pointer.
Qualified variable names are allowed. Member/index paths, arithmetic, casts and calls
in this are not supported yet. The pointer is read once; object address, size and
alignment are checked. Both the object and pointer-variable storage must lie in the
ordinary SRAM window 0x20000000–0x20100000 (exclusive upper bound).
This routing restriction does not prove memory presence/ownership or object lifetime.
The author must reach object initialization and choose a safe execution context.

`signature="unsigned int(unsigned int) const"` specifies return type, explicit parameters
and method qualifiers. Do not include this; use `()` for zero parameters.
Named types/typedefs are resolved by GDB and compared against DWARF types. An overload
without signature remains ambiguous_function; no match produces signature_mismatch;
invalid syntax produces invalid_signature. Multiple exact matches are also refused.

The object type must match exactly; const/volatile are never discarded. A different
object type produces this_type_mismatch, dropping qualifiers produces this_qualifiers,
null/MMIO/misaligned addresses produce invalid_this. this on static/free functions
produces unexpected_this. Inheritance, polymorphic types, ref-qualified methods,
constructors/destructors, operators and template names are outside this subset.
A4.1 scalar argument/return restrictions remain; explicit pointer/reference arguments
are not supported yet. const does not imply side-effect freedom; volatile does not
provide MMIO transport guarantees.

Resolution does not execute target code; the selected linkage symbol is called with
the captured this value. Results and mutations retain this, this_address, this_type,
requested_signature, resolved_function and resolved_signature where applicable.
An unfinished dummy frame is not reported as restored context; side effects are not
rolled back automatically. An async request remains lazy until await.

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

## A4.2 — this / signature

```python
result = await t.call("Probe::choose", 2, this="&probe",
                      signature="unsigned int(int)", timeout=2)
t.check("selected overload", result["return_value"], 5)
```
