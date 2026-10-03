"""E4 bounded Cortex-M finish experiment: hardware return breakpoint, no forced return."""

from dataclasses import dataclass


class FinishError(RuntimeError):
    pass


@dataclass(frozen=True)
class ReturnResult:
    outcome: str
    value_state: str
    value: object
    type_name: str
    breakpoints: tuple
    signal: object


def finish(backend):
    """One continue under the runner's case deadline; never skip another stop."""
    plan = backend.prepare()  # type, caller and hardware capacity before mutation
    point = backend.point(plan)
    primary = None
    try:
        number = point.number  # temporary GDB objects expire at their first hit
        stop = backend.resume()
        numbers = tuple(stop.get('breakpoints', ()))
        # A coincident foreign point is an interruption, not a clean return.
        returned = numbers == (number,) and not stop.get('signal') and backend.at_return(plan)
        if not returned:
            return ReturnResult('interrupted', 'not_returned', None, plan['type_name'],
                                numbers, stop.get('signal'))
        if plan['kind'] == 'void':
            state, value = 'void', None
        else:
            try:
                value = backend.return_value(plan)
                state = 'available'
            except backend.errors:
                state, value = 'unavailable', None
        return ReturnResult('returned', state, value, plan['type_name'], numbers, None)
    except BaseException as exc:
        primary = exc
        raise
    finally:
        try:
            backend.cleanup(point)
        except Exception as cleanup_error:
            if primary is None:
                raise
            # Keep the primary exception and retain cleanup evidence separately.
            backend.cleanup_errors.append(str(cleanup_error))


class CortexMBackend:
    """Explicit scope: normal top frame, ARM 32-bit integer or void C return."""
    def __init__(self, target):
        import gdb
        self.gdb = gdb
        self.target = target
        self.errors = (gdb.error,)
        self.cleanup_errors = []

    def prepare(self):
        g = self.gdb
        thread = g.selected_thread()
        if thread is None or not thread.is_stopped():
            raise FinishError('target must be stopped')
        frame = g.newest_frame()
        if frame.type() != g.NORMAL_FRAME or not frame.architecture().name().startswith('arm'):
            raise FinishError('requires normal ARM top frame')
        caller = frame.older()
        symbol = frame.function()
        if caller is None or symbol is None:
            raise FinishError('caller/function metadata unavailable')
        result_type = symbol.type.target().strip_typedefs()
        if result_type.code == g.TYPE_CODE_VOID:
            kind = 'void'
        elif result_type.code in (g.TYPE_CODE_INT, g.TYPE_CODE_BOOL, g.TYPE_CODE_ENUM) and result_type.sizeof <= 4:
            kind = 'integer'
        else:
            raise FinishError('unsupported return ABI; only <=32-bit integer or void')
        points = [bp for bp in (g.breakpoints() or ()) if bp.is_valid() and bp.enabled]
        if len(points) >= self.target.profile['breakpoint_limit']:
            raise FinishError('no hardware breakpoint headroom')
        return dict(address=int(caller.pc()) & ~1, sp=int(caller.read_register('sp')),
                    kind=kind, type=result_type, type_name=str(result_type))

    def point(self, plan):
        return self.target.breakpoint('*' + hex(plan['address']), temporary=True)

    def resume(self):
        self.target.stops.clear()
        self.gdb.execute('continue')
        return dict(self.target.stops[-1]) if self.target.stops else {}

    def at_return(self, plan):
        frame = self.gdb.newest_frame()
        return int(frame.pc()) == plan['address'] and int(frame.read_register('sp')) == plan['sp']

    def return_value(self, plan):
        # AAPCS integer result, interpreted with the actual return type.
        return int(self.gdb.newest_frame().read_register('r0').cast(plan['type']))

    def cleanup(self, point):
        if point.is_valid():
            point.delete()
