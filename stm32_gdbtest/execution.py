"""Cooperative live execution. GDB APIs run on its main thread (ТЗ API 4.22)."""
import math
import threading
import time

from stm32_gdbtest.errors import ApiError, fail


def timeout_value(value, operation):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value > 0
    except OverflowError:
        valid = False
    if not valid:
        fail(operation, 'validation', 'none', 'invalid_timeout', 'timeout must be finite and positive')
    return float(value)


def wait_deadline(cancelled, deadline):
    """Event.wait may wake before a monotonic deadline, notably on Windows."""
    while not cancelled.is_set():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return True
        cancelled.wait(min(remaining, threading.TIMEOUT_MAX))
    return False


class Request:
    def __init__(self, controller, operation, timeout):
        self.controller, self.operation, self.timeout = controller, operation, timeout
        self.cancelled = threading.Event()
        self.done = None
        self.deadline = None

    def __await__(self):
        result = yield self
        return result


class CoroutineRunner:
    """Only our awaitables are supported; never nest asyncio's event loop inside GDB."""
    def __init__(self, coroutine, gdb, failed):
        self.coroutine, self.gdb, self.failed = coroutine, gdb, failed
        self.finished = False

    def start(self):
        self.step()

    def step(self, value=None, error=None):
        if self.finished:
            return
        try:
            request = self.coroutine.throw(error) if error is not None else self.coroutine.send(value)
            if not isinstance(request, Request):
                self.gdb.post_event(lambda: self.step(error=ApiError(
                    'Only Target execution awaitables are supported', operation='wait',
                    stage='validation', effect='none', code='unsupported_awaitable')))
                return
            request.controller.arm(request, self.step)
        except StopIteration:
            self.finished = True
        except BaseException as cause:
            self.finished = True
            self.failed(cause)


class LiveExecution:
    def __init__(self, target, gdb):
        self.target, self.gdb = target, gdb
        self.generation = 0
        self.stop = None
        self.pending = None
        self.unknown = False
        self.exited = False
        self.interrupt_requested = False
        self.closed = False
        self.listeners = []
        if not callable(getattr(gdb, 'post_event', None)) or not callable(getattr(gdb, 'Thread', None)):
            fail('resume', 'validation', 'none', 'async_unsupported', 'GDB event/thread API unavailable')
        for name, callback in [('stop', self.on_stop), ('cont', self.on_cont), ('exited', self.on_exit)]:
            registry = getattr(gdb.events, name, None)
            if registry is None:
                fail('resume', 'validation', 'none', 'async_unsupported', 'GDB event API unavailable')
        self.route()
        for name, callback in [('stop', self.on_stop), ('cont', self.on_cont), ('exited', self.on_exit)]:
            registry = getattr(gdb.events, name)
            registry.connect(callback)
            self.listeners.append((registry, callback))
        registry = getattr(gdb.events, 'connection_removed', None)
        if registry is not None:
            registry.connect(self.on_disconnect)
            self.listeners.append((registry, self.on_disconnect))

    def route(self):
        if threading.current_thread() is not threading.main_thread():
            fail('resume', 'validation', 'none', 'main_thread_required', 'GDB main thread required')
        g = self.gdb
        if g.parameter('non-stop'):
            fail('resume', 'validation', 'none', 'unsupported_mode', 'Only all-stop is supported')
        inferior = g.selected_inferior()
        if len(g.inferiors()) != 1 or len(inferior.threads()) != 1:
            fail('resume', 'validation', 'none', 'ambiguous_target', 'Exactly one inferior/thread required')
        return g.selected_thread()

    def state(self):
        if self.exited:
            return 'exited'
        try:
            thread = self.gdb.selected_thread()
            if thread is None or not thread.is_valid():
                return 'unknown'
            if self.unknown:
                return 'unknown'
            return 'stopped' if thread.is_stopped() else 'running' if thread.is_running() else 'unknown'
        except Exception:
            return 'unknown'

    def require_stopped(self, operation):
        if getattr(self.target, '_call_incomplete', False):
            fail(operation, 'validation', 'none', 'call_incomplete', 'Inferior call context not restored')
        state = self.state()
        if state != 'stopped':
            fail(operation, 'validation', 'none', 'not_stopped', 'Target is not confirmed stopped', state=state)

    def on_cont(self, event):
        self.stop = None

    def on_stop(self, event):
        self.unknown = False
        self.stop = dict(self.target.stops[-1]) if self.target.stops else dict(breakpoints=[], signal=None)
        self.stop['generation'] = self.generation
        self.notify()

    def on_exit(self, event):
        self.exited = True
        self.stop = dict(kind='exited', generation=self.generation, exit_code=getattr(event, 'exit_code', None))
        self.notify()

    def on_disconnect(self, event):
        self.unknown = True
        self.notify()

    def notify(self):
        request = self.pending
        if request is not None:
            self.gdb.post_event(lambda: self.poll(request))

    def resume(self):
        if hasattr(self.target, '_assert_awaited'):
            self.target._assert_awaited()
        self.require_stopped('resume')
        self.route()
        self.generation += 1
        self.stop = None
        self.target.stops.clear()
        self.interrupt_requested = False
        try:
            self.gdb.execute('continue &', to_string=True)
        except self.gdb.error as cause:
            self.unknown = True
            fail('resume', 'command', 'unknown', 'execution_failed', 'Asynchronous continue failed', cause=cause)
        result = dict(operation='resume', outcome='started', generation=self.generation)
        self.target.record('execution', result)
        return result

    async def wait(self, timeout, operation='wait'):
        timeout = timeout_value(timeout, operation)
        # Enumerating remote threads may issue a target query while running.
        # The single-thread route was checked before continue; await only cached stop state.
        return await Request(self, operation, timeout)

    async def command(self, command, operation, timeout):
        request = Request(self, operation, timeout)
        request.command = command
        result = await request
        if result['outcome'] != 'stopped':
            fail(operation, 'observe', 'unknown', 'operation_timeout', 'Operation did not stop')
        return result

    def arm(self, request, done):
        if self.pending is not None:
            self.gdb.post_event(lambda: done(error=ApiError('Concurrent wait', operation=request.operation,
                code='concurrent_wait', stage='validation', effect='none')))
            return
        request.done = done
        request.deadline = time.monotonic() + request.timeout
        self.pending = request
        try:
            if hasattr(request, 'command'):
                self.require_stopped(request.operation)
                self.route()
                self.generation += 1
                self.stop = None
                self.target.stops.clear()
                self.interrupt_requested = False
                self.gdb.execute(request.command, to_string=True)
            if request.operation == 'halt' and self.state() == 'running':
                self.interrupt_requested = True
                self.gdb.execute('interrupt', to_string=True)
            self.poll(request)
        except BaseException as cause:
            self.unknown = True
            self.complete(request, error=ApiError(str(cause), operation=request.operation,
                stage='command', effect='unknown', code=('execution_failed' if hasattr(request, 'command') else 'interrupt_failed')))
            return
        if self.pending is request:
            def wake():
                if wait_deadline(request.cancelled, request.deadline):
                    self.gdb.post_event(lambda: self.poll(request))
            try:
                self.gdb.Thread(target=wake, daemon=True).start()
            except BaseException as cause:
                self.complete(request, error=ApiError(str(cause), operation=request.operation,
                    stage='observe', effect='unknown', code='timer_failed'))

    def poll(self, request):
        if self.closed or self.pending is not request:
            return
        state = self.state()
        if state in ('stopped', 'exited'):
            stop = dict(self.stop or dict(kind='already_stopped', generation=self.generation))
            if 'kind' not in stop:
                stop['kind'] = self.target._stop_kind(stop)
            # SIGINT is expected only after our interrupt request. Other signals retain their meaning.
            if self.interrupt_requested and stop.get('signal') == 'SIGINT':
                stop['kind'] = 'interrupt'
            result = dict(operation=request.operation, outcome=state, generation=self.generation, stop=stop)
            self.target.report.setdefault('stops', []).append(stop)
            if stop['kind'] in ('fault', 'signal'):
                self.complete(request, error=ApiError('Unexpected target stop', operation=request.operation,
                    stage='observe', effect='completed', code=stop['kind']+'_stop', stop=stop))
            else:
                self.complete(request, result)
        elif state == 'unknown':
            self.complete(request, error=ApiError('Target state unknown', operation=request.operation,
                stage='observe', effect='unknown', code='state_unknown'))
        elif time.monotonic() >= request.deadline:
            if request.operation == 'wait' or hasattr(request, 'command'):
                self.complete(request, dict(operation='wait', outcome='timeout', generation=self.generation))
            else:
                self.unknown = True
                self.complete(request, error=ApiError('Halt not confirmed', operation='halt',
                    stage='observe', effect='unknown', code='halt_timeout'))

    def complete(self, request, result=None, error=None):
        if self.pending is not request:
            return
        self.pending = None
        request.cancelled.set()
        try:
            self.target.record('execution', result if error is None else dict(error=error.details))
        except BaseException as cause:
            error = cause
        self.gdb.post_event(lambda: request.done(result, error))

    def close(self):
        self.closed = True
        if self.pending:
            self.pending.cancelled.set()
            self.pending = None
        for registry, callback in self.listeners:
            registry.disconnect(callback)
        self.listeners.clear()
