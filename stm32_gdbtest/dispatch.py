"""Single-threaded execution dispatch (ТЗ API 4.23)."""
from functools import wraps
from inspect import signature
import time

from stm32_gdbtest.errors import fail
from stm32_gdbtest.execution import Request, timeout_value


class Command:
    def __init__(self, text):
        self.text = text


class Operation:
    """Tracked, lazy awaitable. Creating one never executes target code."""
    def __init__(self, target, name, factory, timeout):
        self.target, self.name, self.factory = target, name, factory
        self.timeout, self.used = timeout, False

    def __await__(self):
        if self.used:
            fail(self.name, 'validation', 'none', 'already_awaited', 'Operation already awaited')
        self.used = True
        self.target._unawaited = None
        return (yield from self.run().__await__())

    async def run(self):
        target = self.target
        live = target._live()
        deadline = min(time.monotonic() + self.timeout, getattr(target, '_deadline', float('inf')))
        generator = self.factory()
        error = None
        try:
            while True:
                try:
                    command = generator.throw(error) if error else next(generator)
                    error = None
                except StopIteration as result:
                    return result.value
                try:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        fail(self.name, 'validation', 'none', 'operation_timeout', 'Deadline expired')
                    await live.command(command.text, self.name, remaining)
                except BaseException as cause:
                    error = cause
        finally:
            generator.close()


class WaitOperation(Operation):
    async def run(self):
        return await self.target._live().wait(self.timeout, self.name)


def execution_method(function):
    """Drive the same generator synchronously or through the GDB event loop."""
    arguments = signature(function)
    @wraps(function)
    def dispatch(target, *args, timeout=None, **kwargs):
        arguments.bind(target, *args, **kwargs)
        live = getattr(target, '_execution', None)
        if function.__name__ == 'resume' and kwargs.get('sync', True) is False:
            if timeout is not None:
                fail('resume', 'validation', 'none', 'invalid_arguments', 'Nonblocking resume has no timeout')
            return target._live().resume()
        if live is not None:
            target._assert_awaited()
            duration = timeout_value(timeout, function.__name__) if timeout is not None else max(0.001, getattr(target, '_deadline', time.monotonic() + 30.0) - time.monotonic())
            operation = Operation(target, function.__name__, lambda: function(target, *args, **kwargs), duration)
            target._unawaited = operation
            return operation
        if timeout is not None:
            fail(function.__name__, 'validation', 'none', 'async_required', 'Explicit navigation timeout requires async def')
        generator = function(target, *args, **kwargs)
        error = None
        try:
            while True:
                try:
                    command = generator.throw(error) if error else next(generator)
                    error = None
                except StopIteration as result:
                    return result.value
                try:
                    # Use the defining module, including the host-test GDB substitute.
                    gdb = function.__globals__['gdb']
                    gdb.execute(command.text, to_string=True)
                except BaseException as cause:
                    error = cause
        finally:
            generator.close()
    return dispatch


class AtomicRequest(Request):
    """An inferior call is bounded by GDB itself, not by stop-event polling."""
    def __init__(self, target, callback, timeout):
        super().__init__(self, 'call', timeout)
        self.target, self.callback, self.used = target, callback, False

    def __await__(self):
        if self.used:
            fail('call', 'validation', 'none', 'already_awaited', 'Call already awaited')
        self.used = True
        self.target._unawaited = None
        return (yield from super().__await__())

    def arm(self, request, done):
        import gdb
        try:
            result = self.callback(self.timeout)
        except BaseException as error:
            gdb.post_event(lambda error=error: done(error=error))
        else:
            gdb.post_event(lambda: done(result))
