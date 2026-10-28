"""Conservative namespace/static resolution before inferior execution (ТЗ API 4.23.7)."""
import re

from stm32_gdbtest.errors import fail
from stm32_gdbtest.expression import parameters


def reject(code, message, function):
    fail('call', 'validation', 'none', code, message, function=function)


def resolve(gdb, function, arguments):
    try:
        return _resolve(gdb, function, arguments)
    except gdb.error as cause:
        fail('call', 'validation', 'none', 'function_unavailable',
             'Cannot resolve callable DWARF function', cause=cause, function=function)


def _resolve(gdb, function, arguments):
    with parameters(gdb, {'may-call-functions': False}):
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
        if len(candidates) != 1:
            reject('ambiguous_function', 'Overloads require explicit selection (not supported yet)', function)
        symbol = next(iter(candidates.values()))
        kind = symbol.type.strip_typedefs()
        if kind.code != gdb.TYPE_CODE_FUNC or '...' in str(kind):
            reject('unsupported_signature', 'Expected a non-variadic function', function)
        fields = kind.fields()
        if any(field.artificial for field in fields):
            reject('unsupported_method', 'Implicit this/ABI arguments are not supported', function)
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
        return linkage, result
