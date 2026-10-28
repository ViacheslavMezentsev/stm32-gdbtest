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

The object type must match exactly or select a base under A4.3b; const/volatile are never discarded. An incompatible
object type produces this_type_mismatch, dropping qualifiers produces this_qualifiers,
null/MMIO/misaligned addresses produce invalid_this. this on static/free functions
produces unexpected_this. Non-virtual inheritance is described in A4.3b. Polymorphic types, ref-qualified methods,
constructors/destructors, operators and template names are outside this subset.
A4.1 scalar returns remain; explicit Pointer/Reference arguments are described in A4.3a below. const does not imply side-effect freedom; volatile does not
provide MMIO transport guarantees.

Resolution does not execute target code; the selected linkage symbol is called with
the captured this value. Results and mutations retain this, this_address, this_type,
requested_signature, resolved_function and resolved_signature where applicable.
An unfinished dummy frame is not reported as restored context; side effects are not
rolled back automatically. An async request remains lazy until await.

Limitations: the call runs on the halted core and changes its state — the function's side effects
are kept; without `timeout=` the call is bounded only by the scenario timeout; pointer returns, floating-point numbers and
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

## A4.3a — Pointer and Reference (0.6.0 candidate)

`from stm32_gdbtest import Pointer, Reference`. These are immutable descriptions,
not addresses or GDB expressions; construction does not access the target. Resolution
happens at call, and only at await in async, with the core stopped.

- `Pointer("samples", count=4)` starts at a named array; count cannot exceed its DWARF extent.
- `Pointer("buffer_ptr", count=4)` reads a named pointer variable once per argument.
- `Pointer("&state")` addresses one named object; count above 1 is refused.
- `Pointer.null()` explicitly passes null to a pointer parameter; null read from a variable is refused.
- `Reference("state")` binds an existing named object without temporaries or user conversions.

Count is in elements, defaults to 1, and accepts integers 1..1048576, not bool.
Explicit null uses count=0. Names are limited to 256 characters and may be qualified.
Member/index paths, arithmetic, casts and calls are unsupported. Bad descriptors
produce invalid_argument.

One T*/T& level supports integer, bool and non-polymorphic class/struct types with inheritance as specified by A4.3b below. Types must match exactly or select one unambiguous base; const/volatile may be added but never removed
(argument_qualifiers). Signatures accept these types and typedefs; overload selection
remains explicit. Descriptors also enable DWARF checking for plain C functions.
T**, void*, function/member pointers, T&&, array references, by-value objects and
pointer/reference returns remain unsupported. An integer is never inferred as an address.

Before execution, size, alignment and the entire ordinary SRAM range
0x20000000–0x20100000 are checked; pointer-variable storage is checked before reading
its value. Errors include argument_range, argument_type_mismatch, argument_qualifiers
and unsupported_argument. Arrays/objects have extent=known; pointer ranges have
extent=declared: the stated count does not prove allocation, ownership or lifetime.
Count does NOT constrain the function body or automatically bind a separate length
argument. MMIO/Flash are excluded.

Arguments retain JSON descriptions; argument_bindings stores path, actual/expected
type, address, count, bytes and extent. Null has zero address/size.
The module adds no post-call content snapshot. Scenarios explicitly check effects,
neighbouring data and restoration. This is not a guarantee of physical GDB-server
access counts; Reference uses dereference of the resolved address in the call expression.
All arguments are checked before the single explicit call; refusal does not invoke it.

```python
from stm32_gdbtest import Pointer, Reference

result = await t.call("demo::sum", Pointer("samples", count=4), 4,
                      signature="unsigned int(const unsigned int *, unsigned int)", timeout=2)
t.check("sum", result["return_value"], 10)
await t.call("demo::bump", Reference("scalar"), signature="void(unsigned int &)", timeout=2)
```


## A4.3b — non-virtual inheritance (0.6.0 candidate)

`call("Base::step", ..., this="&derived")` explicitly selects Base::step.
An exact non-polymorphic type or one unique path from the object's static type to
its base is accepted: single, multi-level and multiple non-virtual inheritance.
There is no inherited-name search for Derived::step: name the declaring class.
Overloads still require an exact signature.

The shared this/Pointer/Reference preflight reads DWARF layout, adds constant byte
offsets and passes the base subobject address. Pointer conversion to a base requires
count=1 even at offset zero: Derived[] is not Base[]. Exact types retain A4.3a rules.
Pointer.null() needs no adjustment; const/volatile can be added, never removed.

Both the source object and adjusted subobject are checked for SRAM range, size,
alignment and containment. Traversal is bounded to 128 nodes and 16 types per path.
Multiple paths produce ambiguous_base; missing, negative or non-byte offsets,
incomplete types and traversal limits produce base_layout_unavailable. Virtual
inheritance/polymorphic source objects produce unsupported_inheritance; existing
unsupported parameter/method refusals remain. Type, qualifier and range errors keep
their existing codes. All refusals precede execution (stage=validation, effect=none).

Validated on ARM GCC/DWARF and GDB using a neutral ELF. No dynamic layout or vtable
reads, downcasts, cross-casts, virtual dispatch or user conversions are supported.
public/private/protected access is not checked: this is debugger layout access, not
a compiler check of a C++ expression. Complete and trustworthy DWARF is a prerequisite;
corrupt metadata cannot prove ABI compatibility. Object lifetime, construction and
ownership remain the author's responsibility. Unknown layout is refused rather
than computed from target object contents.

Call results and audit add this_original_address, this_expected_type,
this_offset_bytes and this_base_path; this_address is the adjusted address passed.
argument_bindings adds original_address, offset_bytes and base_path; address/bytes
describe the passed subobject. The path lists types from source to expected base.
Explicit null has no path/original address.

```python
result = await t.call("Base::step", 3, this="&derived", timeout=2)
t.check("selected subobject", result["this_address"], expected_base_address)
await t.call("inspect_base", Reference("derived"), timeout=2)
```

Omit await in ordinary def. Do compare the address with an independent oracle,
check neighbouring fields and restore changes explicitly. Do not assume a second
base has offset zero, pass Derived[] as Base[], or bypass ambiguity with a cast
expression. Examples/refusals: tests/renode-backend/test_cpp.py, HW_CPP_INHERITANCE_*.
