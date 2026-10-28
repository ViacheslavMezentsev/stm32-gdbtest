"""Typed argument descriptors and memory admission without an inferior."""
import unittest
from dataclasses import FrozenInstanceError
from types import SimpleNamespace as NS
from stm32_gdbtest import ApiError, Pointer, Reference
from stm32_gdbtest.call_arguments import describe
from stm32_gdbtest.cpp_call import bind_argument, parse_type, same_type


class Kind:
    def __init__(self, code=1, name='unsigned int', target=None, size=4, cv='', fields=()):
        self.code, self.name, self._target, self.sizeof, self.cv, self._fields = code, name, target, size, cv, fields
        self.alignof = 4
    def strip_typedefs(self): return self
    def unqualified(self): return Kind(self.code, self.name, self._target, self.sizeof, fields=self._fields)
    def fields(self): return self._fields
    def target(self): return self._target
    def range(self): return (0, 3)
    def __str__(self): return ((self.cv + ' ') if self.cv else '') + self.name
    def __eq__(self, other): return isinstance(other, Kind) and self.code == other.code and str(self) == str(other)


class ArgumentTests(unittest.TestCase):
    def setUp(self):
        self.element = Kind()
        self.parameter = Kind(11, 'unsigned int *', self.element)
        self.value = NS(type=Kind(13, 'unsigned int [4]', self.element, 16), address=0x20000100)
        self.gdb = NS(TYPE_CODE_PTR=11, TYPE_CODE_REF=12, TYPE_CODE_ARRAY=13, TYPE_CODE_STRUCT=10,
                      TYPE_CODE_INT=1, TYPE_CODE_BOOL=2,
                      lookup_symbol=lambda name: (NS(is_variable=True, value=lambda: self.value), False))
    def bind(self, arg): return bind_argument(self.gdb, 'demo::f', self.parameter, arg)
    def refuse(self, arg, code):
        with self.assertRaises(ApiError) as caught: self.bind(arg)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(caught.exception.details['effect'], 'none')

    def test_inert_frozen_and_json_description(self):
        pointer = Pointer('buffer', count=4)
        self.assertEqual(describe(pointer), dict(kind='pointer', path='buffer', count=4))
        with self.assertRaises(FrozenInstanceError): pointer.count = 5
        self.assertEqual(describe(Reference('state')), dict(kind='reference', path='state'))
        self.assertEqual(Pointer.null(), Pointer(None, count=0))

    def test_invalid_paths_counts(self):
        for path in ('p()', '(T*)1', 'a.b', 'a[0]', 'p+1', '', 42):
            for cls in (Pointer, Reference):
                with self.subTest(path=path, cls=cls):
                    with self.assertRaises(ApiError): cls(path)
        for count in (0, -1, True, 1.5, 0x100001):
            with self.assertRaises(ApiError): Pointer('p', count=count)
        with self.assertRaises(ApiError): Reference('&state')

    def test_array_extent_and_bytes(self):
        expression, audit = self.bind(Pointer('buffer', count=4))
        self.assertEqual(expression, '(unsigned int *)536871168')
        self.assertEqual(audit['bytes'], 16)
        self.assertEqual(audit['extent'], 'known')
        self.refuse(Pointer('buffer', count=5), 'argument_range')

    def test_null_only_explicit_pointer(self):
        self.assertEqual(self.bind(Pointer.null())[1]['address'], 0)
        self.parameter = Kind(12, 'unsigned int &', self.element)
        self.refuse(Pointer.null(), 'argument_type_mismatch')
        self.value = NS(type=self.element, address=0)
        self.refuse(Reference('state'), 'argument_range')

    def test_object_reference_and_single_object_extent(self):
        self.value = NS(type=self.element, address=0x20000100)
        self.refuse(Pointer('&state', count=2), 'argument_range')
        self.parameter = Kind(12, 'unsigned int &', self.element)
        expression, audit = self.bind(Reference('state'))
        self.assertEqual(expression, '*((unsigned int *)536871168)')
        self.assertEqual(audit['bytes'], 4)

    def test_sram_alignment_and_overflow(self):
        for address in (0, 0x40000000, 0x20000101, 0x200ffffc):
            self.value.address = address
            self.refuse(Pointer('buffer', count=4), 'argument_range')

    def test_pointer_read_once_slot_before_read(self):
        reads = []
        class Value:
            type = Kind(11, 'unsigned int *', Kind())
            address = 0x20000040
            def __int__(self): reads.append(1); return 0x20000100
        self.value = Value()
        self.assertEqual(self.bind(Pointer('p', count=4))[1]['extent'], 'declared')
        self.assertEqual(reads, [1])
        self.value.address = 0x40000000
        self.refuse(Pointer('p'), 'argument_range')
        self.assertEqual(reads, [1])

    def test_const_volatile_and_exact_type(self):
        self.value = NS(type=Kind(cv='const volatile'), address=0x20000100)
        self.refuse(Pointer('&state'), 'argument_qualifiers')
        self.parameter = Kind(11, 'const volatile unsigned int *', self.value.type)
        self.bind(Pointer('&state'))
        self.value.type = Kind(name='int')
        self.refuse(Pointer('&state'), 'argument_type_mismatch')

    def test_signature_typedef_keeps_const(self):
        self.gdb.lookup_type = lambda name: Kind(cv='const')
        expected = parse_type(self.gdb, 'Readonly *', 'demo::f')
        self.assertTrue(same_type(self.gdb, Kind(11, 'const unsigned int *', Kind(cv='const')), expected))
        self.assertFalse(same_type(self.gdb, self.parameter, expected))

    def test_no_nested_pointer_or_inheritance(self):
        self.parameter = Kind(11, 'unsigned int **', Kind(11, 'unsigned int *', self.element))
        self.refuse(Pointer.null(), 'unsupported_argument')
        for field in (NS(is_base_class=True, name='Base'), NS(is_base_class=False, name='_vptr.Probe')):
            self.parameter = Kind(11, 'Probe *', Kind(10, 'Probe', fields=[field]))
            self.refuse(Pointer('&probe'), 'unsupported_argument')
