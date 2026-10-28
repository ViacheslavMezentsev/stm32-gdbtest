"""Resolver refuses unsupported C++ before any expression execution."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock
from stm32_gdbtest import ApiError
from stm32_gdbtest.cpp_call import resolve
from gdb_parameters import install


class Kind:
    def __init__(self, code, name='unsigned int', fields=(), result=None):
        self.code, self.name, self._fields, self._result = code, name, fields, result
        self.sizeof = 4
    def strip_typedefs(self): return self
    def fields(self): return self._fields
    def target(self): return self._result
    def __str__(self): return self.name


class CppCallTests(unittest.TestCase):
    def setUp(self):
        self.scalar = Kind(1)
        self.field = NS(artificial=False, type=self.scalar)
        self.kind = Kind(7, fields=[self.field], result=self.scalar)
        self.symbol = NS(name='demo::f(unsigned int)', linkage_name='_Zf', type=self.kind,
                         value=lambda: NS(is_optimized_out=False, address=0x8000100))
        self.gdb = NS(error=RuntimeError, TYPE_CODE_FUNC=7, TYPE_CODE_INT=1,
                      TYPE_CODE_BOOL=2, TYPE_CODE_VOID=3,
                      Value=lambda n: NS(cast=lambda kind: (2**32-1) if str(kind).startswith('unsigned') else -1),
                      decode_line=lambda name: (None, [NS(pc=1)]),
                      block_for_pc=lambda pc: NS(function=self.symbol),
                      parse_and_eval=Mock(side_effect=AssertionError('unexpected evaluation')),
                      execute=lambda *a, **kw: None)
        install(self.gdb)

    def refuse(self, code, arguments=(1,)):
        before = self.gdb.parameter('may-call-functions')
        with self.assertRaises(ApiError) as caught:
            resolve(self.gdb, 'demo::f', arguments)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.details["effect"], 'none')
        self.assertEqual(self.gdb.parameter('may-call-functions'), before)
        self.gdb.parse_and_eval.assert_not_called()

    def test_bound_symbol_and_no_execution(self):
        self.assertEqual(resolve(self.gdb, 'demo::f', (1,)), ('_Zf', self.scalar, [], {}))
        self.gdb.parse_and_eval.assert_not_called()

    def test_overloads(self):
        other = NS(**vars(self.symbol)); other.linkage_name = '_Zother'
        self.gdb.decode_line = lambda name: (None, [NS(pc=1), NS(pc=2)])
        self.gdb.block_for_pc = lambda pc: NS(function=self.symbol if pc == 1 else other)
        self.refuse('ambiguous_function')

    def test_constructor_refused_before_symbol_lookup(self):
        self.gdb.decode_line = Mock(side_effect=AssertionError('must refuse before lookup'))
        with self.assertRaises(ApiError) as caught:
            resolve(self.gdb, 'Probe::Probe', (), this='&probe')
        self.assertEqual(caught.exception.code, 'unsupported_method')
        self.gdb.decode_line.assert_not_called()

    def test_exact_extern_c_signature_is_quoted(self):
        self.symbol.linkage_name = 'demo::f(unsigned int)'
        result = resolve(self.gdb, 'demo::f', (1,))
        self.assertEqual(result[0], "'demo::f(unsigned int)'")
        self.symbol.linkage_name = "demo::f(unsigned int);evil()"
        self.refuse('unsupported_function')

    def test_missing(self):
        self.gdb.decode_line = Mock(side_effect=RuntimeError('absent'))
        self.refuse('function_unavailable')

    def test_implicit_this(self):
        self.field.artificial = True
        self.refuse('unsupported_method')

    def test_types_and_ranges(self):
        for value, code in [(1.5, 'unsupported_argument'), ('f()', 'unsupported_argument'),
                            (-1, 'argument_range'), (2**32, 'argument_range')]:
            with self.subTest(value=value): self.refuse(code, (value,))
        self.field.type = Kind(9, 'int *')
        self.refuse('unsupported_argument')

    def test_arity_and_result(self):
        self.refuse('argument_count', ())
        self.kind._result = Kind(9, 'Object')
        self.refuse('unsupported_return')

    def test_variadic_and_code_absent(self):
        self.kind.name = 'int (...)'
        self.refuse('unsupported_signature')
        self.kind.name = 'int (unsigned int)'
        self.symbol.value = lambda: NS(is_optimized_out=True, address=None)
        self.refuse('function_unavailable')


class ObjectKind:
    alignof = 4
    code = 10
    sizeof = 4
    def __init__(self, name='Probe', cv='', fields=()):
        self.name, self.cv, self._fields = name, cv, fields
    def strip_typedefs(self): return self
    def unqualified(self): return ObjectKind(self.name, fields=self._fields)
    def fields(self): return self._fields
    def __str__(self): return (self.cv + ' ' + self.name).strip()
    def __eq__(self, other): return isinstance(other, ObjectKind) and str(self) == str(other)


class PointerKind:
    code = 11
    sizeof = 4
    def __init__(self, target): self._target = target
    def strip_typedefs(self): return self
    def unqualified(self): return self
    def target(self): return self._target
    def __str__(self): return str(self._target) + ' *'


class ObjectTests(unittest.TestCase):
    def setUp(self):
        from stm32_gdbtest.cpp_call import object_argument
        self.operation = object_argument
        self.obj = ObjectKind()
        self.pointer = PointerKind(self.obj)
        self.value = NS(type=self.obj, address=0x20000100)
        self.symbol = NS(is_variable=True, value=lambda: self.value)
        self.gdb = NS(TYPE_CODE_PTR=11, TYPE_CODE_STRUCT=10, lookup_symbol=lambda n: (self.symbol, False))
        self.method = NS(name='Probe::add(unsigned int)')

    def invoke(self, path='&probe'):
        return self.operation(self.gdb, 'Probe::add', self.method, self.pointer, path)

    def refuse(self, code, path='&probe'):
        with self.assertRaises(ApiError) as caught: self.invoke(path)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.details['effect'], 'none')

    def test_address_without_reading_contents(self):
        expression, meta = self.invoke()
        self.assertEqual(expression, ['(Probe *)536871168'])
        self.assertEqual(meta['this_address'], 0x20000100)

    def test_cv_never_dropped(self):
        from stm32_gdbtest.cpp_call import qualifiers
        for cv in ('const', 'volatile', 'const volatile'):
            with self.subTest(cv=cv):
                self.value.type = ObjectKind(cv=cv)
                self.assertEqual(qualifiers(self.value.type), set(cv.split()))
                self.refuse('this_qualifiers')
                self.pointer = PointerKind(self.value.type)
                self.invoke()
                self.pointer = PointerKind(self.obj)

    def test_sram_and_type(self):
        for address in (0, 0x40000000, 0x200fffff, 0x20000101):
            self.value.address = address
            self.refuse('invalid_this')
        self.value.address = 0x20000100
        self.value.type = ObjectKind('Other')
        self.refuse('this_type_mismatch')

    def test_bases_virtual_and_reference_qualifier(self):
        for field in (NS(is_base_class=True, name='Base'), NS(is_base_class=False, name='_vptr.Probe')):
            self.pointer = PointerKind(ObjectKind(fields=[field]))
            self.refuse('unsupported_method')
        self.pointer = PointerKind(self.obj)
        self.method.name = 'Probe::add(unsigned int) &'
        self.refuse('unsupported_method')

    def test_pointer_read_once_and_mmio_slot_not_read(self):
        reads = []
        class Value:
            type = PointerKind(ObjectKind())
            address = 0x20000020
            def __int__(self): reads.append(1); return 0x20000100
        self.value = Value()
        self.invoke('probe_ptr')
        self.assertEqual(len(reads), 1)
        self.value.address = 0x40000000
        self.refuse('invalid_this', 'probe_ptr')
        self.assertEqual(len(reads), 1)

    def test_signature_types_and_syntax(self):
        from stm32_gdbtest.cpp_call import parse_signature
        scalar = Kind(1)
        gdb = NS(error=RuntimeError, lookup_type=lambda n: scalar)
        result, args, cv = parse_signature(gdb, 'unsigned int(unsigned int) const volatile', 'Probe::f')
        self.assertIs(result, scalar)
        self.assertEqual(args, [scalar])
        self.assertEqual(cv, {'const', 'volatile'})
        for text in ('int(*)()', 'int(f())', 'int(int**)', 42, 'int() &'):
            with self.assertRaises(ApiError): parse_signature(gdb, text, 'Probe::f')
