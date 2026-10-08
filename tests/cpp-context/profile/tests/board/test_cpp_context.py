"""
RU: C++-контекст: this, перегрузки, преобразование типов и границы видимости.
EN: C++ context: this, overloads, type conversion and scope boundaries.
"""
import gdb
from stm32_gdbtest import case


# Keep missing and optimized-out values distinct from an actual numeric zero.
def inspect_local(frame, name, convert):
    try:
        value = frame.read_var(name)
        if value.is_optimized_out:
            return {"state": "optimized_out", "type": str(value.type)}
        value.fetch_lazy()
        return {"state": "available", "type": str(value.type), "value": convert(value)}
    except (gdb.error, ValueError) as error:
        return {"state": "unavailable", "error": str(error)}


# Observe naturally executed overloads; do not inject calls or rewrite objects.
@case("HW_CPP_CONTEXT", timeout_s=60)
def cpp_context(t):
    t.reach("process_cpp")
    t.check("global object field", t.read("converter.bias"), 7)
    address = t.evaluate("&converter", as_type=int)

    # Explicit signatures distinguish overloads independently of frame-name normalization.
    for signature, argument, expected, convert in (("int", 4, 11, int), ("float", 1.5, 8.5, float)):
        location = "Converter::apply(" + signature + ") const"
        location = "'" + location + "'" if signature == "float" else location
        reached = t.reach(location)
        t.check("original linespec retained", reached["location"], location)
        frame = gdb.newest_frame()
        obj = inspect_local(frame, "this", int)
        parameter = inspect_local(frame, "input", convert)
        t.record("cpp.context", {"signature": signature, "this": obj, "input": parameter,
                                 "frames": t.frames(4)["frames"]})
        t.check("this is available", obj["state"], "available")
        t.check("this identifies converter", obj["value"], address)
        t.check("field in method context", t.evaluate("this->bias", as_type=int), 7)
        if parameter["state"] == "available":
            t.check("overload argument", parameter["value"], argument)

        # Cast a typed pointer using native GDB Python, then read its field.
        typed = frame.read_var("this").cast(gdb.lookup_type("Converter").pointer())
        t.check("typed dereference", int(typed.dereference()["bias"]), 7)
        returned = t.finish()
        t.record("cpp.return", {"signature": signature, "result": returned})
        if returned["return_state"] == "available":
            t.check("observed return", returned["return_value"], expected)

    # Published sinks are independent of whether GDB could recover a return value.
    t.reach("process_cpp")
    t.check("integer sink", t.read("int_sink"), 11)
    t.check("float sink", t.read("float_sink"), 8.5)
    missing = inspect_local(gdb.newest_frame(), "input", int)
    t.record("cpp.outside", missing)
    t.check("method argument out of scope", missing["state"], "unavailable")
    t.check("missing value not replaced with zero", "value" in missing, False)
