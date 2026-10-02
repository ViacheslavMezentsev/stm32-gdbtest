"""R5: compare natural capture, forced return and direct invocation by ABI type."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


TYPES = {
    'WIDE': ('calculate_wide', 'accepted_wide', 'sample.wide_value',
             '(uint64_t)0xfedcba9876543210ULL', 0x123456789abcdef9, 0xfedcba9876543210),
    'FLOAT': ('calculate_gain', 'accepted_gain', 'sample.gain', '(float)-2.5', 4.75, -2.5),
    'STRUCT': ('transform_pair', 'accepted_pair', 'pair_input', 'pair_input',
               {'code': -8, 'count': 20}, {'code': -7, 'count': 19}),
}


def materialize(kind, value):
    if kind == 'STRUCT':
        return {name: int(value[name]) for name in ('code', 'count')}
    return float(value) if kind == 'FLOAT' else int(value)


def exercise(t, kind, mode):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set displaced-stepping off')
    gdb.execute('set debug remote on')
    sample = gdb.lookup_global_symbol('sample').value()
    fn, sink, argument, substitution, natural, forced = TYPES[kind]
    with Research(t, (int(sample.address), int(sample.type.sizeof))) as r:
        r.record('operation', {'kind': kind, 'mode': mode, 'natural': natural, 'forced': forced})
        if mode == 'CALL':
            r.run_until('process_returns')
            frame = gdb.newest_frame()
            before = {'pc': int(frame.pc()), 'sp': int(frame.read_register('sp'))}
            data = bytes(gdb.selected_inferior().read_memory(*r.ram))
            value = gdb.parse_and_eval(fn + '(' + argument + ')')
            actual = materialize(kind, value)
            r.record('direct_value', actual)
            t.check('direct return value', actual, natural)
            frame = gdb.newest_frame()
            t.check('direct call restores PC SP', {'pc': int(frame.pc()),
                    'sp': int(frame.read_register('sp'))}, before)
            t.check('sample unchanged', bytes(gdb.selected_inferior().read_memory(*r.ram)).hex(), data.hex())
        else:
            r.run_until(fn)
            t.check('natural caller', gdb.newest_frame().older().name(), 'process_returns')
            if mode == 'FINISH':
                bp = gdb.FinishBreakpoint(gdb.newest_frame(), internal=True)
                r.owned.append(bp)
                number = bp.number
                gdb.execute('continue')
                r.record('finish_stop', dict(r.last_stop or {}))
                t.check('finish point identity', number in (r.last_stop or {}).get('breakpoints', []), True)
                r.record('capture_available', bp.return_value is not None)
                t.check('finish return available', bp.return_value is not None, True)
                actual = materialize(kind, bp.return_value)
                r.record('captured_value', actual)
                t.check('captured return value', actual, natural)
            else:
                gdb.execute('return ' + substitution)
            t.check('caller selected', gdb.newest_frame().name(), 'process_returns')
        r.run_until('process_returns')
        actual = materialize(kind, gdb.parse_and_eval(sink))
        r.record('caller_value', actual)
        t.check('caller consumed result', actual, forced if mode == 'RETURN' else natural)
        r.run_until('process_returns')
        t.check('next natural result', materialize(kind, gdb.parse_and_eval(sink)), natural)


@case('HW_R5_WIDE_FINISH', labels=('research', 'abi'))
def wide_finish(t):
    exercise(t, 'WIDE', 'FINISH')


@case('HW_R5_WIDE_RETURN', labels=('research', 'abi'))
def wide_return(t):
    exercise(t, 'WIDE', 'RETURN')


@case('HW_R5_WIDE_CALL', labels=('research', 'abi'))
def wide_call(t):
    exercise(t, 'WIDE', 'CALL')


@case('HW_R5_FLOAT_FINISH', labels=('research', 'abi'))
def float_finish(t):
    exercise(t, 'FLOAT', 'FINISH')


@case('HW_R5_FLOAT_RETURN', labels=('research', 'abi'))
def float_return(t):
    exercise(t, 'FLOAT', 'RETURN')


@case('HW_R5_FLOAT_CALL', labels=('research', 'abi'))
def float_call(t):
    exercise(t, 'FLOAT', 'CALL')


@case('HW_R5_STRUCT_FINISH', labels=('research', 'abi'))
def struct_finish(t):
    exercise(t, 'STRUCT', 'FINISH')


@case('HW_R5_STRUCT_RETURN', labels=('research', 'abi'))
def struct_return(t):
    exercise(t, 'STRUCT', 'RETURN')


@case('HW_R5_STRUCT_CALL', labels=('research', 'abi'))
def struct_call(t):
    exercise(t, 'STRUCT', 'CALL')
