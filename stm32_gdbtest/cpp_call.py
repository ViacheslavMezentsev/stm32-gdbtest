"""Conservative namespace/static resolution before inferior execution (ТЗ API 4.23.7)."""
import re

from stm32_gdbtest.errors import fail
from stm32_gdbtest.expression import parameters


def reject(code, message, function):
    fail('call', 'validation', 'none', code, message, function=function)


def resolve(gdb, function, arguments, *, this=None, signature=None):
    try:
        return _resolve(gdb, function, arguments, this, signature)
    except gdb.error as cause:
        fail('call', 'validation', 'none', 'function_unavailable',
             'Cannot resolve callable DWARF function', cause=cause, function=function)


def _resolve(gdb, function, arguments, this, signature):
    parts = function.split('::')
    if len(parts) > 1 and parts[-1] == parts[-2]:
        reject('unsupported_method', 'Constructors are not supported', function)
    if this is not None and (type(this) is not str or not THIS.fullmatch(this)):
        reject('invalid_this', 'Use &object or a named pointer; expressions are not supported', function)
    with parameters(gdb, {'may-call-functions': False}):
        requested = parse_signature(gdb, signature, function) if signature is not None else None
        try:
            rest, locations = gdb.decode_line(function)
        except gdb.error as cause:
            fail('call', 'validation', 'none', 'function_unavailable',
                 'No callable DWARF function', cause=cause, function=function)
        candidates = {}
        for location in locations or ():
            block = gdb.block_for_pc(location.pc)
            while block is not None and block.function is None:
                block = block.superblock
            if block is None:
                reject('function_unavailable', 'No function block', function)
            symbol = block.function
            if symbol.name.split('(', 1)[0] != function:
                reject('unsupported_function', 'Resolved name does not match exactly', function)
            candidates[(symbol.linkage_name, int(symbol.value().address or 0))] = symbol
        if rest or not candidates:
            reject('function_unavailable', 'No exact function with code', function)
        if requested is not None:
            candidates = {key: sym for key, sym in candidates.items()
                          if matches(sym, requested)}
            if not candidates:
                reject('signature_mismatch', 'No exact DWARF signature matches', function)
        if len(candidates) != 1:
            reject('ambiguous_function', 'Overloads require explicit selection (not supported yet)', function)
        symbol = next(iter(candidates.values()))
        kind = symbol.type.strip_typedefs()
        if kind.code != gdb.TYPE_CODE_FUNC or '...' in str(kind):
            reject('unsupported_signature', 'Expected a non-variadic function', function)
        fields = kind.fields()
        implicit, metadata = [], {}
        if any(field.artificial for field in fields):
            if this is None:
                reject('unsupported_method', 'This method requires explicit this', function)
            if not fields[0].artificial or any(f.artificial for f in fields[1:]):
                reject('unsupported_method', 'Unsupported implicit ABI arguments', function)
            implicit, metadata = object_argument(gdb, function, symbol, fields[0].type, this)
            fields = fields[1:]
        elif this is not None:
            reject('unexpected_this', 'Static/free functions do not take this', function)
        if len(fields) != len(arguments):
            reject('argument_count', 'Argument count differs from DWARF', function)
        result = kind.target().strip_typedefs()
        if result.code not in (gdb.TYPE_CODE_INT, gdb.TYPE_CODE_BOOL, gdb.TYPE_CODE_VOID):
            reject('unsupported_return', 'Only integer, bool and void results are supported', function)
        for field, value in zip(fields, arguments):
            argtype = field.type.strip_typedefs()
            if argtype.code not in (gdb.TYPE_CODE_INT, gdb.TYPE_CODE_BOOL) or type(value) not in (int, bool):
                reject('unsupported_argument', 'Only integer and bool arguments are supported', function)
            bits = argtype.sizeof * 8
            # A debugger-owned scalar cast follows the target ABI, including plain char.
            unsigned = int(gdb.Value(-1).cast(argtype)) >= 0
            low, high = (0, 1) if argtype.code == gdb.TYPE_CODE_BOOL else (
                (0, (1 << bits) - 1) if unsigned else (-(1 << (bits - 1)), (1 << (bits - 1)) - 1))
            if not low <= value <= high:
                reject('argument_range', 'Argument does not fit its declared type', function)
        linkage = symbol.linkage_name
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', linkage or ''):
            reject('unsupported_function', 'No supported linkage name', function)
        # Bind the call to this symbol, not a second overload-resolution operation.
        value = symbol.value()
        if value.is_optimized_out or value.address is None or int(value.address) == 0:
            reject('function_unavailable', 'Function has no callable address', function)
        if this is not None or signature is not None:
            metadata.update(resolved_function=symbol.name, requested_signature=signature,
                            resolved_signature=str(kind))
        return linkage, result, implicit, metadata


# No GDB expressions: address of one named object, or one named pointer variable.
THIS = re.compile(r'&?[A-Za-z_][A-Za-z_0-9]*(?:::[A-Za-z_][A-Za-z_0-9]*)*')
TYPE = r'[A-Za-z_][A-Za-z_0-9: ]*'
SIGNATURE = re.compile(r'(' + TYPE + r')\(([^()]*)\)\s*(const(?:\s+volatile)?|volatile(?:\s+const)?)?')


def parse_signature(gdb, text, function):
    if type(text) is not str or len(text) > 512:
        reject('invalid_signature', 'Expected a bounded scalar signature', function)
    match = SIGNATURE.fullmatch(text.strip())
    if match is None:
        reject('invalid_signature', 'Use return_type(argument_types) [const] [volatile]', function)
    result, arguments, quals = match.groups()
    names = [] if not arguments.strip() else arguments.split(',')
    if any(not re.fullmatch(TYPE, n.strip()) for n in names):
        reject('invalid_signature', 'Only named scalar types are supported', function)
    try:
        types = [gdb.lookup_type(n.strip()).strip_typedefs() for n in [result, *names]]
    except gdb.error as cause:
        fail('call', 'validation', 'none', 'invalid_signature', 'Unknown signature type',
             cause=cause, function=function)
    return types[0], types[1:], set((quals or '').split())


def qualifiers(kind):
    # GDB const()/volatile() can replace, rather than combine, qualifiers.
    # Here kind is a non-template object type, not a pointer declarator.
    return set(re.findall(r'\b(const|volatile)\b', str(kind)))


def matches(symbol, requested):
    kind = symbol.type.strip_typedefs()
    fields = list(kind.fields())
    quals = set()
    if fields and fields[0].artificial:
        quals = qualifiers(fields[0].type.strip_typedefs().target().strip_typedefs())
        fields = fields[1:]
    result, arguments, expected_quals = requested
    return (kind.target().strip_typedefs() == result and quals == expected_quals
            and len(fields) == len(arguments)
            and all(not f.artificial and f.type.strip_typedefs() == t
                    for f, t in zip(fields, arguments)))


def sram(address, size, function):
    if size <= 0 or not 0x20000000 <= address < address + size <= 0x20100000:
        reject('invalid_this', 'Object and pointer storage must be in ordinary SRAM', function)


def object_argument(gdb, function, method, pointer_type, path):
    pointer_type = pointer_type.strip_typedefs()
    if pointer_type.code != gdb.TYPE_CODE_PTR:
        reject('unsupported_method', 'Implicit argument is not an object pointer', function)
    expected = pointer_type.target().strip_typedefs()
    if expected.code != gdb.TYPE_CODE_STRUCT or '&' in method.name.split(')', 1)[-1]:
        reject('unsupported_method', 'Only unqualified-by-reference class methods are supported', function)
    if any(getattr(f, 'is_base_class', False) or (f.name or '').startswith('_vptr')
           for f in expected.unqualified().fields()):
        reject('unsupported_method', 'Inheritance and polymorphic objects are not supported', function)
    symbol = gdb.lookup_symbol(path.lstrip('&'))[0]
    if symbol is None or not symbol.is_variable:
        reject('invalid_this', 'Object/pointer variable is absent', function)
    value = symbol.value()
    if path.startswith('&'):
        actual = value.type.strip_typedefs()
        address = int(value.address) if value.address is not None else 0
    else:
        if value.type.strip_typedefs().code != gdb.TYPE_CODE_PTR or value.address is None:
            reject('invalid_this', 'Expected a pointer variable in SRAM', function)
        sram(int(value.address), value.type.sizeof, function)
        actual = value.type.strip_typedefs().target().strip_typedefs()
        address = int(value)  # Read the pointer once, never its object contents.
    if actual.unqualified() != expected.unqualified():
        reject('this_type_mismatch', 'Exact object type required; no base adjustment', function)
    if not qualifiers(actual) <= qualifiers(expected):
        reject('this_qualifiers', 'Cannot discard const/volatile from the object', function)
    sram(address, actual.sizeof, function)
    if actual.alignof <= 0 or address % actual.alignof:
        reject('invalid_this', 'Object pointer is not aligned for its type', function)
    # Trusted DWARF type spelling, restricted to a named struct and cv qualifiers.
    spelling = str(pointer_type.unqualified())
    if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9: ]* \*', spelling):
        reject('unsupported_method', 'Unsupported this type spelling', function)
    return [f'({spelling}){address}'], dict(this=path, this_address=address, this_type=str(actual))
