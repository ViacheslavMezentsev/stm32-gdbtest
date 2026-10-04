"""Typed reading and writing of debugged objects (ТЗ API 0.3.0, 4.2/4.6).

RU: Преобразование `gdb.Value` в простые типы Python и проверка записанного значения.
EN: Conversion of `gdb.Value` into plain Python types and verification of a written value.
"""

import re

from stm32_gdbtest.errors import fail

# Fallback type codes for host checks, where GDB is not importable; a live GDB module wins.
FALLBACK_CODES = {
    "TYPE_CODE_INT": 8,
    "TYPE_CODE_ENUM": 9,
    "TYPE_CODE_BOOL": 11,
    "TYPE_CODE_CHAR": 9,
    "TYPE_CODE_FLT": 12,
    "TYPE_CODE_STRING": 15,
    "TYPE_CODE_ARRAY": 16,
    "TYPE_CODE_STRUCT": 13,
    "TYPE_CODE_UNION": 14,
    "TYPE_CODE_VOID": 10,
}
SCALAR_TYPES = ("TYPE_CODE_INT", "TYPE_CODE_ENUM", "TYPE_CODE_BOOL", "TYPE_CODE_CHAR", "TYPE_CODE_FLT")
STRUCT_TYPES = ("TYPE_CODE_STRUCT", "TYPE_CODE_UNION")


def type_constant(name, gdb=None):
    """Numeric value of a GDB type code.

    A live GDB module is the source of truth because the numbers differ between versions; the
    fallback table keeps the pure-Python checks working when GDB cannot be imported.
    """
    if gdb is None:
        try:
            import gdb as module
        except ModuleNotFoundError:
            module = None
    else:
        module = gdb
    if module is not None:
        value = getattr(module, name, None)
        if value is not None:
            return value
    return FALLBACK_CODES.get(name)


def type_code(value, gdb=None):
    """Type code of a value after removing qualifiers and typedefs; None when unavailable."""
    kind = value.type
    # Volatile and const qualifiers carry their own code and hide the compound type underneath.
    unqualified = getattr(kind, "unqualified", None)
    if callable(unqualified):
        try:
            candidate = unqualified()
        except Exception:
            candidate = None
        if candidate is not None:
            kind = candidate
    strip = getattr(kind, "strip_typedefs", None)
    if callable(strip):
        candidate = strip()
        if candidate is not None:
            kind = candidate
    return getattr(kind, "code", None)


def value_to_plain(value, path, gdb=None):
    """Convert a scalar, string, array or struct value into a plain Python object.

    Scalar conversion follows the declared type: floats stay floats and booleans become bools, so a
    scenario does not have to guess what `read` returned.
    """
    code = type_code(value, gdb)
    if code is not None and code == type_constant("TYPE_CODE_FLT", gdb):
        return float(value)
    if code is not None and code == type_constant("TYPE_CODE_BOOL", gdb):
        return bool(value)
    if code is not None and code in [type_constant(name, gdb) for name in SCALAR_TYPES]:
        return int(value)
    if code is not None and code == type_constant("TYPE_CODE_STRING", gdb):
        return value.string()
    if code is not None and code == type_constant("TYPE_CODE_ARRAY", gdb):
        return [value_to_plain(element, f"{path}[{index}]", gdb)
                for index, element in enumerate(array_elements(value, path, gdb=gdb))]
    if code is not None and code in [type_constant(name, gdb) for name in STRUCT_TYPES]:
        plain = unqualified_type(value.type)
        return {field.name: value_to_plain(value[field.name], f"{path}.{field.name}", gdb)
                for field in plain.fields()}
    fail("read", "observe", "none", "unsupported_type", f"unsupported type for {path}",
         path=path, type_code=code)


def unqualified_type(kind):
    """Type without volatile/const qualifiers, which is required for field access."""
    unqualified = getattr(kind, "unqualified", None)
    if callable(unqualified):
        try:
            candidate = unqualified()
        except Exception:
            candidate = None
        if candidate is not None:
            kind = candidate
    return kind


def array_elements(value, path, start=0, count=None, gdb=None):
    """Elements of an array value for [start, start+count); count=None reads the rest."""
    bounds = value.type.range()
    low, high = bounds[0], bounds[1]
    step = bounds[2] if len(bounds) > 2 and bounds[2] is not None else 1
    if step != 1:
        fail("read", "validation", "none", "unsupported_type",
             f"array step {step} is not supported for {path}", path=path, step=step)
    length = high - low + 1
    if type(start) is not int or start < 0 or start > length:
        fail("read", "validation", "none", "invalid_slice", f"invalid start {start!r} for {path}",
             start=start, length=length)
    if count is not None and (type(count) is not int or count < 0):
        fail("read", "validation", "none", "invalid_slice", f"invalid count {count!r} for {path}",
             count=count)
    stop = length if count is None else min(length, start + count)
    return [value[low + index] for index in range(start, stop)]


def invalid_path(path):
    """Diagnostic for an empty or non-string path."""
    return fail("read", "validation", "none", "invalid_path", "path must be a non-empty string",
                path=path)


def optimized_out(path, expression):
    """Diagnostic for a value the compiler left unavailable at the current stop."""
    return fail("read", "observe", "none", "optimized_out",
                f"value is optimized out: {expression}", path=path)


def conversion_failed(path, expression, cause):
    """Diagnostic for a value GDB refused to read at the current stop."""
    return fail("read", "readback", "none", "conversion_failed",
                f"conversion failed for {expression}", cause=cause, path=path)


def verification_failed(path, written, read_back):
    """Diagnostic for a value that did not survive the read-back check."""
    return fail("write", "readback", "partial", "verification_failed",
                f"written value {written!r} read back as {read_back!r}",
                path=path, written=written, read_back=read_back)


def return_type_shape(kind):
    """Name, signedness and width in bits of a declared return type.

    A width of zero means the type cannot carry an integer value; the caller reports it. Signedness
    comes from the type name first, because GDB reports `unsigned int` and `int` with the same code.
    """
    if kind is None:
        return (None, False, 0)
    code = type_code_of(kind)
    size = getattr(kind, "sizeof", None)
    name = getattr(kind, "name", None)
    # Some GDB builds report sizeof==1 for void, so the type code decides first.
    if code is None or code == type_constant("TYPE_CODE_VOID") or not size:
        return (name, False, 0)
    label = name or ""
    logical = code in (type_constant("TYPE_CODE_BOOL"), type_constant("TYPE_CODE_CHAR"))
    # Signedness is not exposed by the GDB type API, so the name is the evidence: `unsigned`,
    # `uint32_t`, `u8`, `uintptr_t` and friends are unsigned, everything else is treated as signed.
    unsigned = logical or "unsigned" in label or label.startswith(("uint", "u8", "u16", "u32", "u64"))
    return (name or str(code), not unsigned, int(size) * 8)


def type_code_of(kind):
    """Type code of a declared type object, without qualifiers or typedefs."""
    if kind is None:
        return None
    unqualified = getattr(kind, "unqualified", None)
    if callable(unqualified):
        try:
            candidate = unqualified()
        except Exception:
            candidate = None
        if candidate is not None:
            kind = candidate
    strip = getattr(kind, "strip_typedefs", None)
    if callable(strip):
        candidate = strip()
        if candidate is not None:
            kind = candidate
    return getattr(kind, "code", None)


def argument_literal(value):
    """GDB literal of one scalar argument; a non-finite float cannot be expressed in C.

    Returns None when the value cannot be passed by value.
    """
    if type(value) is bool:
        return "1" if value else "0"
    if type(value) is int:
        return str(value)
    if type(value) is float:
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return repr(value)
    if type(value) is str:
        # A plain GDB expression is passed through: identifiers, member paths, casts and `&object`.
        stripped = value.strip()
        if not stripped or len(stripped) > 120:
            return None
        if re.fullmatch(r"[A-Za-z_&][\w.&\->()\[\] ]*", stripped) is None:
            return None
        return stripped
    return None


# Names of the declared kinds that cannot be a watched object.
_NON_WATCHABLE = ("*", "(", "[", "void")


def non_watchable(kind):
    """Reason why a declared kind cannot be watched, or None when it can.

    The kind name is used because type-code constants are unavailable when GDB is not loaded and a
    wrong lookup would silently accept a pointer as a watchable object.
    """
    name = (getattr(kind, "name", None) or "").strip()
    if not name:
        return None
    if name.endswith("*") or "(*" in name:
        return "pointer"
    if "(" in name and name.endswith(")"):
        return "function"
    if name == "void":
        return "void"
    return None
