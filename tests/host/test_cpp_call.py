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
        self.assertEqual(resolve(self.gdb, 'demo::f', (1,)), ('_Zf', self.scalar))
        self.gdb.parse_and_eval.assert_not_called()

    def test_overloads(self):
        other = NS(**vars(self.symbol)); other.linkage_name = '_Zother'
        self.gdb.decode_line = lambda name: (None, [NS(pc=1), NS(pc=2)])
        self.gdb.block_for_pc = lambda pc: NS(function=self.symbol if pc == 1 else other)
        self.refuse('ambiguous_function')

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
