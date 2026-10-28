"""Conservative namespace/static resolution before inferior execution (ТЗ API 4.23.7)."""
import re
from dataclasses import dataclass
from stm32_gdbtest.call_arguments import Pointer, Reference
from stm32_gdbtest import values

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
                          if matches(sym, requested, gdb)}
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
        literals, bindings = [], []
        for index, (field, value) in enumerate(zip(fields, arguments)):
            argtype = field.type.strip_typedefs()
            if type(value) in (Pointer, Reference):
                literal, binding = bind_argument(gdb, function, argtype, value)
                literals.append(literal)
                bindings.append(dict(index=index, **binding))
                continue
            literals.append(values.argument_literal(value))
            if argtype.code not in (gdb.TYPE_CODE_INT, gdb.TYPE_CODE_BOOL) or type(value) not in (int, bool):
                reject('unsupported_argument', 'Only integer and bool arguments are supported', function)
            bits = argtype.sizeof * 8
            # A debugger-owned scalar cast follows the target ABI, including plain char.
            unsigned = int(gdb.Value(-1).cast(argtype)) >= 0
            low, high = (0, 1) if argtype.code == gdb.TYPE_CODE_BOOL else (
                (0, (1 << bits) - 1) if unsigned else (-(1 << (bits - 1)), (1 << (bits - 1)) - 1))
            if not low <= value <= high:
                reject('argument_range', 'Argument does not fit its declared type', function)
        if bindings:
            metadata.update(argument_bindings=bindings, _argument_literals=literals)
        linkage = symbol.linkage_name
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', linkage or ''):
            # Some extern-C DWARF exposes the full signature as linkage_name.
            # Quote only the exact selected symbol, never user-supplied GDB text.
            if (not isinstance(linkage, str) or len(linkage) > 512
                    or not linkage.startswith(function + '(')
                    or not re.fullmatch(r'[A-Za-z_0-9: (),*&]+', linkage)):
                reject('unsupported_function', 'No supported linkage name', function)
            linkage = "'" + linkage + "'"
        # Bind the call to this symbol, not a second overload-resolution operation.
        value = symbol.value()
        if value.is_optimized_out or value.address is None or int(value.address) == 0:
            reject('function_unavailable', 'Function has no callable address', function)
        if this is not None or signature is not None or bindings:
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
    try:
        types = [parse_type(gdb, n.strip(), function) for n in [result, *names]]
    except gdb.error as cause:
        fail('call', 'validation', 'none', 'invalid_signature', 'Unknown signature type',
             cause=cause, function=function)
    return types[0], types[1:], set((quals or '').split())


def qualifiers(kind):
    # GDB const()/volatile() can replace, rather than combine, qualifiers.
    # Here kind is a non-template object type, not a pointer declarator.
    return set(re.findall(r'\b(const|volatile)\b', str(kind)))


def matches(symbol, requested, gdb):
    kind = symbol.type.strip_typedefs()
    fields = list(kind.fields())
    quals = set()
    if fields and fields[0].artificial:
        quals = qualifiers(fields[0].type.strip_typedefs().target().strip_typedefs())
        fields = fields[1:]
    result, arguments, expected_quals = requested
    return (same_type(gdb, kind.target(), result) and quals == expected_quals
            and len(fields) == len(arguments)
            and all(not f.artificial and same_type(gdb, f.type, t)
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


@dataclass(frozen=True)
class TypeSpec:
    base: object
    cv: frozenset
    indirect: str | None
    outer_cv: frozenset


def parse_type(gdb, name, function):
    match = re.fullmatch(r'([A-Za-z_][A-Za-z_0-9: ]*?)(?:\s*([*&])\s*((?:(?:const|volatile)\s*)*))?', name)
    if match is None:
        reject('invalid_signature', 'Only one pointer/reference level and named types are supported', function)
    base, indirect, outer = match.groups()
    cv = frozenset(re.findall(r'\b(const|volatile)\b', base))
    base = re.sub(r'\b(const|volatile)\b', '', base)
    kind = gdb.lookup_type(' '.join(base.split())).strip_typedefs()
    if not cv and not indirect:
        return kind
    if indirect == '&' and outer:
        reject('invalid_signature', 'References cannot have outer cv qualifiers', function)
    return TypeSpec(kind, cv | frozenset(qualifiers(kind)), indirect, frozenset((outer or '').split()))


def same_type(gdb, actual, expected):
    actual = actual.strip_typedefs()
    if isinstance(expected, TypeSpec):
        if expected.indirect:
            code = gdb.TYPE_CODE_PTR if expected.indirect == '*' else gdb.TYPE_CODE_REF
            if actual.code != code:
                return False
            tail = str(actual).rsplit('*', 1)[-1] if code == gdb.TYPE_CODE_PTR else ''
            if set(re.findall(r'\b(const|volatile)\b', tail)) != expected.outer_cv:
                return False
            actual = actual.target().strip_typedefs()
        return actual.unqualified() == expected.base.unqualified() and qualifiers(actual) == expected.cv
    expected = expected.strip_typedefs()
    # GDB equality alone is insufficient for const/volatile combinations.
    if actual.code != expected.code:
        return False
    if actual.code in (getattr(gdb, 'TYPE_CODE_PTR', -1), getattr(gdb, 'TYPE_CODE_REF', -2)):
        return str(actual) == str(expected) and same_type(gdb, actual.target(), expected.target())
    return actual == expected and qualifiers(actual) == qualifiers(expected)


def argument_sram(address, size, alignment, function):
    if (size <= 0 or not 0x20000000 <= address < address + size <= 0x20100000
            or alignment <= 0 or address % alignment):
        reject('argument_range', 'Argument range/alignment is outside ordinary SRAM', function)


def bind_argument(gdb, function, parameter, descriptor):
    reference = type(descriptor) is Reference
    code = gdb.TYPE_CODE_REF if reference else gdb.TYPE_CODE_PTR
    if parameter.code != code:
        reject('argument_type_mismatch', 'Descriptor kind differs from parameter type', function)
    expected = parameter.target().strip_typedefs()
    if expected.code not in (gdb.TYPE_CODE_INT, gdb.TYPE_CODE_BOOL, gdb.TYPE_CODE_STRUCT):
        reject('unsupported_argument', 'Unsupported pointee/referent type', function)
    if expected.code == gdb.TYPE_CODE_STRUCT and any(
            getattr(f, 'is_base_class', False) or (f.name or '').startswith('_vptr')
            for f in expected.unqualified().fields()):
        reject('unsupported_argument', 'Inheritance and polymorphic arguments are not supported', function)
    spelling = str(expected)
    if not re.fullmatch(TYPE, spelling):
        reject('unsupported_argument', 'Unsupported pointee spelling', function)
    if not reference and descriptor.path is None:
        return f'({spelling} *)0', dict(kind='pointer', path=None, actual_type=None,
                                       expected_type=str(parameter), address=0, count=0, bytes=0)
    path = descriptor.path
    symbol = gdb.lookup_symbol(path.lstrip('&'))[0]
    if symbol is None or not symbol.is_variable:
        reject('invalid_argument', 'Argument variable is absent', function)
    value = symbol.value()
    actual = value.type.strip_typedefs()
    count = 1 if reference else descriptor.count
    known = None
    if not reference and not path.startswith('&') and actual.code == gdb.TYPE_CODE_ARRAY:
        low, high = actual.range()
        if low != 0:
            reject('unsupported_argument', 'Only zero-based arrays are supported', function)
        known = high - low + 1
        actual = actual.target().strip_typedefs()
        address = int(value.address) if value.address is not None else 0
    elif not reference and not path.startswith('&') and actual.code == gdb.TYPE_CODE_PTR:
        if value.address is None:
            reject('invalid_argument', 'Pointer must be stored in SRAM', function)
        argument_sram(int(value.address), actual.sizeof, actual.alignof, function)
        actual = actual.target().strip_typedefs()
        address = int(value)  # Capture exactly once before any target execution.
    else:
        if not reference and not path.startswith('&'):
            reject('invalid_argument', 'Use &object, a named array, or a named pointer', function)
        known = 1
        address = int(value.address) if value.address is not None else 0
    if actual.unqualified() != expected.unqualified():
        reject('argument_type_mismatch', 'Exact pointee/referent type required', function)
    if not qualifiers(actual) <= qualifiers(expected):
        reject('argument_qualifiers', 'Cannot discard const/volatile', function)
    if known is not None and count > known:
        reject('argument_range', 'Count exceeds the named object/array extent', function)
    size = actual.sizeof * count
    argument_sram(address, size, actual.alignof, function)
    expression = f'({spelling} *){address}'
    if reference:
        expression = '*(' + expression + ')'
    return expression, dict(kind='reference' if reference else 'pointer', path=path,
                            actual_type=str(actual), expected_type=str(parameter), address=address,
                            count=count, bytes=size, extent='known' if known is not None else 'declared')
