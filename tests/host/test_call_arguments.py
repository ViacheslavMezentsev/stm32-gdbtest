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
        for field, code in ((NS(is_base_class=True, name='Base'), 'base_layout_unavailable'),
                            (NS(is_base_class=False, name='_vptr.Probe'), 'unsupported_argument')):
            self.parameter = Kind(11, 'Probe *', Kind(10, 'Probe', fields=[field]))
            self.refuse(Pointer('&probe'), code)


class InheritanceTests(unittest.TestCase):
    bind = ArgumentTests.bind
    refuse = ArgumentTests.refuse
    def setUp(self):
        ArgumentTests.setUp(self)
        self.base = Kind(10, 'Base')
        self.left = Kind(10, 'Left')
        self.derived = Kind(10, 'Derived', size=12, fields=[self.edge(self.left, 0), self.edge(self.base, 32)])
        self.parameter = Kind(11, 'Base *', self.base)
        self.value = NS(type=self.derived, address=0x20000100)

    @staticmethod
    def edge(kind, bits):
        return NS(is_base_class=True, name=str(kind), type=kind, bitpos=bits)

    # Do not inherit the scalar/array suite: this fixture is a class hierarchy.

    def test_second_base_pointer_and_reference(self):
        expression, audit = self.bind(Pointer('&derived'))
        self.assertEqual(audit['address'], 0x20000104)
        self.assertEqual(audit['original_address'], 0x20000100)
        self.assertEqual(audit['offset_bytes'], 4)
        self.assertEqual(audit['base_path'], ['Derived', 'Base'])
        self.assertEqual(audit['bytes'], 4)
        self.parameter = Kind(12, 'Base &', self.base)
        self.assertEqual(self.bind(Reference('derived'))[1]['address'], 0x20000104)

    def test_chain_and_exact_derived(self):
        self.value.type = Kind(10, 'Deep', size=16, fields=[self.edge(self.derived, 32)])
        self.assertEqual(self.bind(Pointer('&deep'))[1]['offset_bytes'], 8)
        self.parameter = Kind(11, 'Deep *', self.value.type)
        self.assertEqual(self.bind(Pointer('&deep'))[1]['offset_bytes'], 0)

    def test_diamond_ambiguous_even_same_offset(self):
        self.value.type = Kind(10, 'Diamond', size=24, fields=[self.edge(self.derived, 0), self.edge(self.derived, 0)])
        self.refuse(Pointer('&diamond'), 'ambiguous_base')

    def test_unknown_negative_nonbyte_and_outside_offsets(self):
        for bits in (None, -32, 1, 96, True):
            self.value.type = Kind(10, 'Bad', size=12, fields=[self.edge(self.base, bits)])
            self.refuse(Pointer('&bad'), 'base_layout_unavailable')

    def test_virtual_or_polymorphic_source(self):
        edge = self.edge(self.base, 0); edge.is_virtual_base_class = True
        self.value.type = Kind(10, 'Virtual', fields=[edge])
        self.refuse(Pointer('&virtual'), 'unsupported_inheritance')
        self.value.type = Kind(10, 'Virtual', fields=[NS(name='_vptr.Virtual', is_base_class=False)])
        self.refuse(Pointer('&virtual'), 'unsupported_inheritance')

    def test_count_and_qualifiers(self):
        self.refuse(Pointer('&derived', count=2), 'argument_range')
        self.value.type = Kind(10, 'Derived', size=12, cv='const', fields=self.derived.fields())
        self.refuse(Pointer('&derived'), 'argument_qualifiers')
        self.parameter = Kind(11, 'const Base *', Kind(10, 'Base', cv='const'))
        self.assertEqual(self.bind(Pointer('&derived'))[1]['offset_bytes'], 4)

    def test_source_extent_checked_not_only_base(self):
        self.value.address = 0x200ffff8
        self.refuse(Pointer('&derived'), 'argument_range')

    def test_downcast_rejected(self):
        self.value.type = self.base
        self.parameter = Kind(11, 'Derived *', self.derived)
        self.refuse(Pointer('&base'), 'argument_type_mismatch')

    def test_cycle_and_depth_bound(self):
        recursive = Kind(10, 'Cycle')
        recursive._fields = [self.edge(recursive, 0)]
        self.value.type = recursive
        self.refuse(Pointer('&cycle'), 'base_layout_unavailable')
        chain = self.base
        for i in range(17):
            chain = Kind(10, 'Level' + str(i), fields=[self.edge(chain, 0)])
        self.value.type = chain
        self.refuse(Pointer('&deep'), 'base_layout_unavailable')


    def test_this_uses_same_adjustment(self):
        from stm32_gdbtest.cpp_call import object_argument
        expression, audit = object_argument(self.gdb, 'Base::step', NS(name='Base::step(unsigned int)'),
                                             self.parameter, '&derived')
        self.assertEqual(expression, ['(Base *)536871172'])
        self.assertEqual(audit['this_original_address'], 0x20000100)
        self.assertEqual(audit['this_address'], 0x20000104)
        self.assertEqual(audit['this_base_path'], ['Derived', 'Base'])

    def test_zero_offset_conversion_still_refuses_array(self):
        self.value.type = Kind(10, 'One', size=8, fields=[self.edge(self.base, 0)])
        self.refuse(Pointer('&one', count=2), 'argument_range')

    def test_pointer_slot_read_once_with_adjustment(self):
        reads = []
        derived = self.derived
        class Value:
            type = Kind(11, 'Derived *', derived)
            address = 0x20000040
            def __int__(self): reads.append(1); return 0x20000100
        self.value = Value()
        self.assertEqual(self.bind(Pointer('p'))[1]['address'], 0x20000104)
        self.assertEqual(reads, [1])

    def test_graph_size_bound_and_incomplete_type(self):
        self.value.type = Kind(10, 'Wide', size=512, fields=[self.edge(self.base, i*32) for i in range(128)])
        self.refuse(Pointer('&wide'), 'base_layout_unavailable')
        self.value.type = Kind(10, 'Incomplete', size=0)
        self.refuse(Pointer('&incomplete'), 'base_layout_unavailable')


    def test_unavailable_layout_metadata(self):
        class MissingAlignment(Kind):
            def unqualified(self): return self
            @property
            def alignof(self): raise RuntimeError('DWARF alignment unavailable')
            @alignof.setter
            def alignof(self, value): pass
        self.gdb.error = RuntimeError
        self.value.type = MissingAlignment(10, 'Missing')
        self.refuse(Pointer('&missing'), 'base_layout_unavailable')
