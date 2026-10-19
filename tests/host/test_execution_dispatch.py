"""Deferred commands, bounded calls and expression guard (ТЗ API 4.23)."""
import types
import unittest
from unittest.mock import patch
import time

from stm32_gdbtest.dispatch import execution_method, Command, AtomicRequest, WaitOperation
from stm32_gdbtest.execution import CoroutineRunner
from stm32_gdbtest.expression import parameters, evaluate
from stm32_gdbtest.errors import ApiError
import test_live_execution as fixtures
from gdb_parameters import install

class DispatcherTests(fixtures.LiveTests):
    # Inherit the event/timeout matrix as well as its deterministic fake GDB.
    def target_for_dispatch(self):
        t=self.target
        t._execution=self.live
        t._live=lambda:self.live
        def check():
            if getattr(t,'_unawaited',None) is not None:
                raise ApiError('missing await',code='unawaited_operation')
        t._assert_awaited=check
        return t

    def test_incomplete_call_blocks_resume(self):
        self.target._call_incomplete = True
        with self.assertRaises(ApiError) as caught: self.live.resume()
        self.assertEqual(caught.exception.code,'call_incomplete')
        self.assertEqual(self.commands,[])

    def test_command_waits_for_delayed_stop(self):
        async def body(): self.values.append(await self.live.command('continue &','step',1))
        CoroutineRunner(body(),self.g,self.errors.append).start();self.drain()
        self.assertTrue(self.running);self.assertFalse(self.values)
        self.stop('step');self.assertEqual(self.values[0]['outcome'],'stopped')

    def test_command_timeout_is_not_stop(self):
        async def body(): await self.live.command('continue &','step',1)
        CoroutineRunner(body(),self.g,self.errors.append).start();self.drain()
        self.live.pending.deadline=0;self.live.poll(self.live.pending);self.drain()
        self.assertEqual(self.errors[-1].code,'operation_timeout')
        self.assertTrue(self.running)

    def test_lazy_dispatch_repeat_and_missing_await(self):
        @execution_method
        def step(t):
            yield Command('continue &')
            return 42
        t=self.target_for_dispatch()
        operation=step(t)
        self.assertEqual(self.commands,[])
        with self.assertRaises(ApiError): step(t)
        async def body(): self.values.append(await operation)
        CoroutineRunner(body(),self.g,self.errors.append).start();self.drain()
        self.stop('step');self.assertEqual(self.values,[42])
        CoroutineRunner(body(),self.g,self.errors.append).start();self.drain()
        self.assertEqual(self.errors[-1].code,'already_awaited')

    def test_wait_operation_is_tracked(self):
        t=self.target_for_dispatch()
        operation=WaitOperation(t,'wait',None,1)
        t._unawaited=operation
        with self.assertRaises(ApiError): t._assert_awaited()
        async def body(): self.values.append(await operation)
        CoroutineRunner(body(),self.g,self.errors.append).start();self.drain()
        self.assertEqual(self.values[0]['outcome'],'stopped')
        self.assertIsNone(t._unawaited)

    def test_atomic_error_and_single_execution(self):
        t=self.target_for_dispatch();effects=[]
        def callback(seconds): effects.append(seconds);raise ValueError('primary')
        request=AtomicRequest(t,callback,2)
        async def body(): await request
        with patch.dict('sys.modules',gdb=self.g):
            CoroutineRunner(body(),self.g,self.errors.append).start();self.drain()
            CoroutineRunner(body(),self.g,self.errors.append).start();self.drain()
        self.assertEqual(effects,[2]);self.assertIsInstance(self.errors[0],ValueError)
        self.assertEqual(self.errors[1].code,'already_awaited')

class ParameterTests(unittest.TestCase):
    def gdb(self):
        g=types.SimpleNamespace(execute=lambda *a,**kw:'',parse_and_eval=lambda x: x)
        install(g);return g
    def test_restore_initial_and_nested(self):
        g=self.gdb()
        with parameters(g,{'may-call-functions':False}):
            self.assertFalse(g.parameter('may-call-functions'))
            self.assertEqual(evaluate(g,'x'),'x')
            self.assertFalse(g.parameter('may-call-functions'))
        self.assertTrue(g.parameter('may-call-functions'))
    def test_unsupported_fails_before_expression(self):
        g=self.gdb();g.parameter=lambda n:(_ for _ in ()).throw(KeyError(n))
        with self.assertRaises(ApiError) as caught: evaluate(g,'x')
        self.assertEqual(caught.exception.code,'unsupported_gdb_parameter')
    def test_primary_survives_cleanup_error(self):
        g=self.gdb();original=g.execute
        def execute(command,**kw):
            if command.endswith(' on'): raise RuntimeError('restore failed')
            return original(command,**kw)
        g.execute=execute
        with self.assertRaises(ValueError) as caught:
            with parameters(g,{'may-call-functions':False}): raise ValueError('primary')
        self.assertEqual(str(caught.exception),'primary')
        self.assertEqual(len(caught.exception.parameter_cleanup_errors),1)
        self.assertEqual(len(g._stm32_parameter_cleanup_errors),1)

if __name__=='__main__': unittest.main()
