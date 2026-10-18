"""Live execution state, events and failure paths (ТЗ API 4.22)."""
import asyncio
from collections import deque
import tempfile
from pathlib import Path
import types
import unittest
from unittest.mock import patch

from stm32_gdbtest.execution import LiveExecution, CoroutineRunner, timeout_value
from stm32_gdbtest.errors import ApiError
from stm32_gdbtest.collect import collect
from stm32_gdbtest.scenario import invoke, invoke_async


class Event:
    def __init__(self): self.callbacks = []
    def connect(self, f): self.callbacks.append(f)
    def disconnect(self, f): self.callbacks.remove(f)
    def emit(self, value=None):
        for f in list(self.callbacks): f(value)


class LiveTests(unittest.TestCase):
    def setUp(self):
        self.queue, self.commands, self.journal = deque(), [], []
        self.running, self.valid, self.fail_command = False, True, False
        thread = types.SimpleNamespace(is_valid=lambda:self.valid,
            is_stopped=lambda:not self.running, is_running=lambda:self.running)
        inferior = types.SimpleNamespace(threads=lambda:[thread])
        self.g = types.SimpleNamespace(error=RuntimeError, post_event=self.queue.append,
            Thread=lambda **kw:types.SimpleNamespace(start=lambda:None),
            parameter=lambda name:False, selected_thread=lambda:thread,
            selected_inferior=lambda:inferior, inferiors=lambda:[inferior],
            events=types.SimpleNamespace(stop=Event(),cont=Event(),exited=Event()), execute=self.execute)
        self.target=types.SimpleNamespace(stops=[],report={},record=lambda n,d:self.journal.append(d),
            _stop_kind=lambda s:s.get('test_kind','breakpoint'))
        self.live=LiveExecution(self.target,self.g)
        self.addCleanup(self.live.close)
        self.values=[];self.errors=[]

    def execute(self, command, **kwargs):
        self.commands.append(command)
        if self.fail_command: raise RuntimeError('lost transport')
        if command=='continue &':
            self.running=True
            self.g.events.cont.emit()

    def drain(self):
        while self.queue: self.queue.popleft()()

    def run_wait(self, operation='wait', timeout=1):
        async def body():
            self.values.append(await self.live.wait(timeout,operation))
        self.runner=CoroutineRunner(body(),self.g,self.errors.append)
        self.runner.start();self.drain()

    def stop(self, kind='breakpoint', signal=None):
        self.running=False
        self.target.stops.append(dict(test_kind=kind,signal=signal))
        self.g.events.stop.emit();self.drain()

    def test_timeout_is_passive(self):
        self.live.resume();self.run_wait()
        request=self.live.pending;request.deadline=0
        self.live.poll(request);self.drain()
        self.assertEqual(self.values[-1]['outcome'],'timeout')
        self.assertEqual(self.commands,['continue &'])
        self.assertTrue(self.running)

    def test_halt_waits_for_confirmation(self):
        self.live.resume();self.run_wait('halt')
        self.assertFalse(self.values)
        self.assertEqual(self.commands,['continue &','interrupt'])
        self.stop('signal','SIGINT')
        self.assertEqual(self.values[-1]['stop']['kind'],'interrupt')

    def test_halt_timeout_marks_unknown(self):
        self.live.resume();self.run_wait('halt');self.live.pending.deadline=0
        self.live.poll(self.live.pending);self.drain()
        self.assertEqual(self.errors[-1].code,'halt_timeout')
        self.assertEqual(self.live.state(),'unknown')
        with self.assertRaises(ApiError): self.live.require_stopped('read')

    def test_already_stopped_no_interrupt(self):
        self.run_wait('halt')
        self.assertEqual(self.values[-1]['outcome'],'stopped')
        self.assertEqual(self.commands,[])

    def test_early_stop_before_wait(self):
        self.live.resume();self.stop();self.run_wait()
        self.assertEqual(self.values[-1]['stop']['kind'],'breakpoint')

    def test_obsolete_timeout_cannot_finish_new_wait(self):
        self.live.resume();self.run_wait();old=self.live.pending
        self.stop();self.live.resume();self.run_wait()
        self.live.poll(old);self.drain()
        self.assertEqual(len(self.values),1)
        self.stop()
        self.assertEqual(self.values[-1]['generation'],2)

    def test_invalid_timeout_no_command(self):
        for value in [0,-1,True,'1',float('nan'),float('inf')]:
            with self.assertRaises(ApiError):timeout_value(value,'wait')
        self.assertFalse(self.commands)

    def test_transport_loss_is_not_timeout(self):
        self.live.resume();self.run_wait();self.valid=False
        self.live.poll(self.live.pending);self.drain()
        self.assertEqual(self.errors[-1].code,'state_unknown')

    def test_resume_error_no_retry(self):
        self.fail_command=True
        with self.assertRaises(ApiError):self.live.resume()
        self.assertEqual(self.commands,['continue &'])
        self.assertEqual(self.live.state(),'unknown')

    def test_interrupt_error_no_retry(self):
        self.live.resume();self.fail_command=True;self.run_wait('halt')
        self.assertEqual(self.errors[-1].code,'interrupt_failed')
        self.assertEqual(self.commands,['continue &','interrupt'])

    def test_fault_preserved(self):
        self.live.resume();self.run_wait();self.stop('fault')
        self.assertEqual(self.errors[-1].code,'fault_stop')

    def test_exit_is_distinct(self):
        self.live.resume();self.run_wait()
        self.g.events.exited.emit(types.SimpleNamespace(exit_code=0));self.drain()
        self.assertEqual(self.values[-1]['outcome'],'exited')

    def test_unsupported_api_refused(self):
        self.g.Thread=None
        with self.assertRaises(ApiError):LiveExecution(self.target,self.g)
        self.assertFalse(self.commands)

    def test_nonstop_refused(self):
        self.g.parameter=lambda n:True
        with self.assertRaises(ApiError):self.live.resume()
        self.assertFalse(self.commands)

    def test_close_cancels_callbacks(self):
        self.live.resume();self.run_wait();request=self.live.pending
        self.live.close();self.live.poll(request);self.drain()
        self.assertTrue(request.cancelled.is_set())
        self.assertFalse(self.values)
        self.runner.coroutine.close()

    def test_foreign_awaitable_rejected(self):
        class Foreign:
            def __await__(self):yield object()
        async def body():await Foreign()
        CoroutineRunner(body(),self.g,self.errors.append).start();self.drain()
        self.assertEqual(self.errors[-1].code,'unsupported_awaitable')

    def test_async_metadata_and_verdicts(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d,'test_a.py').write_text('@case("HW_ASYNC")\nasync def scenario(t): pass\n')
            self.assertEqual(collect([Path(d)])[0]['function'],'scenario')
        async def body(t): t.report['checks']=[dict(name='caught',passed=False)]
        with self.assertRaises(ApiError):asyncio.run(invoke_async(body,self.target))
        self.target.report['checks']=[]
        invoke(lambda t:None,self.target)

    def test_interrupt_stop_race_keeps_breakpoint(self):
        self.live.resume();self.run_wait('halt');self.stop('breakpoint')
        self.assertEqual(self.values[-1]['stop']['kind'],'breakpoint')

    def test_hidden_coroutine_in_sync_scenario_rejected(self):
        async def body(): pass
        with self.assertRaises(ApiError):invoke(lambda t:body(),self.target)

    def test_mmio_guard_precedes_transport(self):
        from stm32_gdbtest.mmio import GdbTransport
        transport=GdbTransport(object(),{},lambda:False)
        with self.assertRaisesRegex(ValueError,'not_stopped'):transport.prepare()

    def test_audit_failure_resumes_with_error(self):
        self.live.resume();self.run_wait()
        self.target.record=lambda *args:(_ for _ in ()).throw(ValueError('journal full'))
        self.stop()
        self.assertIsInstance(self.errors[-1],ValueError)
        self.assertIsNone(self.live.pending)

    def test_timer_failure_resumes_with_error(self):
        self.live.resume()
        self.g.Thread=lambda **kw:(_ for _ in ()).throw(RuntimeError('cannot start timer'))
        self.run_wait()
        self.assertEqual(self.errors[-1].code,'timer_failed')

    def test_timer_rechecks_early_wakeup(self):
        from stm32_gdbtest.execution import wait_deadline
        waits=[]
        cancelled=types.SimpleNamespace(is_set=lambda:False,wait=waits.append)
        with patch('stm32_gdbtest.execution.time.monotonic',side_effect=[.5,.9,1.0]):
            self.assertTrue(wait_deadline(cancelled,1.0))
        self.assertEqual(len(waits),2)

    def test_cancelled_timer_posts_nothing(self):
        from stm32_gdbtest.execution import wait_deadline
        cancelled=types.SimpleNamespace(is_set=lambda:True)
        self.assertFalse(wait_deadline(cancelled,1.0))

    def test_mmio_thread_check_precedes_state_callback(self):
        from stm32_gdbtest.mmio import GdbTransport
        calls=[]
        transport=GdbTransport(object(),{},lambda:calls.append('state'))
        with patch('stm32_gdbtest.mmio.threading.current_thread',return_value=object()):
            with self.assertRaisesRegex(ValueError,'main_thread_required'):transport.prepare()
        self.assertEqual(calls,[])
