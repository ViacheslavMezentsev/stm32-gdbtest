"""R18: trivial aggregates and explicit C++ overload selection."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


KINDS = {
    'SMALL': ('small_transform', 'small_input', 'small_sink', {'value': 20}, {'value': 10}),
    'PAIR': ('pair_transform', 'pair_input', 'pair_sink', {'code': -8, 'count': 20}, {'code': -7, 'count': 19}),
    'HFA': ('hfa_transform', 'hfa_input', 'hfa_sink', {'x': 2.5, 'y': 4.5}, {'x': 1.5, 'y': 2.5}),
    'INT': ("'Converter::apply(int) const'", '4', 'int_sink', 11, 42),
    'FLOAT': ("'Converter::apply(float) const'", '(float)1.5', 'float_sink', 8.5, -2.5),
}


def convert(kind, value):
    if kind in ('SMALL', 'PAIR', 'HFA'):
        return {name: float(value[name]) if kind == 'HFA' else int(value[name])
                for name in KINDS[kind][3]}
    return float(value) if kind == 'FLOAT' else int(value)


def exercise(t, mode, kinds):
    for command in ('monitor gdb_breakpoint_override hard', 'monitor debug_level 3',
                    'set breakpoint auto-hw on', 'set displaced-stepping off', 'set debug remote on'):
        gdb.execute(command)
    obj = gdb.lookup_global_symbol('converter').value()
    with Research(t, (int(obj.address), int(obj.type.sizeof))) as r:
        r.record('mode', mode)
        if 'INT' in kinds:
            before = {bp.number for bp in (gdb.breakpoints() or ())}
            try:
                r.breakpoint('Converter::apply')
            except ValueError as exc:
                t.check('overload ambiguity rejected', str(exc), 'Missing or ambiguous breakpoint location')
                r.record('overload_rejection', str(exc))
            else:
                raise RuntimeError('Ambiguous overload accepted')
            t.check('ambiguous point removed', {bp.number for bp in (gdb.breakpoints() or ())} == before, True)
        for kind in kinds:
            fn, argument, sink, natural, forced = KINDS[kind]
            if mode == 'CALL':
                r.run_until('process_cpp')
                frame = gdb.newest_frame()
                before = dict(pc=int(frame.pc()), sp=int(frame.read_register('sp')))
                expression = ('converter.apply' if kind in ('INT', 'FLOAT') else fn) + '(' + argument + ')'
                result = convert(kind, gdb.parse_and_eval(expression))
                r.record(kind.lower() + '_call', dict(expression=expression, result=result))
                t.check(kind + ' direct value', result, natural)
                frame = gdb.newest_frame()
                t.check(kind + ' PC SP restored', dict(pc=int(frame.pc()), sp=int(frame.read_register('sp'))), before)
            else:
                r.run_until(fn)
                frame = gdb.newest_frame()
                t.check(kind + ' caller', frame.older().name().removesuffix('()'), 'process_cpp')
                if kind in ('INT', 'FLOAT'):
                    t.check(kind + ' this', int(frame.read_var('this')), int(obj.address))
                    t.check(kind + ' argument', convert(kind, frame.read_var('input')), 4 if kind == 'INT' else 1.5)
                if mode == 'FINISH':
                    bp = gdb.FinishBreakpoint(frame, internal=True)
                    r.owned.append(bp)
                    number = bp.number
                    gdb.execute('continue')
                    t.check(kind + ' finish identity', number in (r.last_stop or {}).get('breakpoints', []), True)
                    t.check(kind + ' captured value available', bp.return_value is not None, True)
                    result = convert(kind, bp.return_value)
                    r.record(kind.lower() + '_finish', result)
                    t.check(kind + ' captured result', result, natural)
                else:
                    replacement = argument if kind in ('SMALL', 'PAIR', 'HFA') else str(forced)
                    if len(kinds) == 1:
                        r.record('return_intent', dict(kind=kind, replacement=replacement, expected=forced))
                    gdb.execute('return ' + replacement)
                t.check(kind + ' caller after return', gdb.newest_frame().name().removesuffix('()'), 'process_cpp')
            r.run_until('process_cpp')
            actual = convert(kind, gdb.parse_and_eval(sink))
            r.record(kind.lower() + '_sink', dict(actual=actual, expected=forced if mode == 'RETURN' else natural))
            t.check(kind + ' caller consumed value', actual, forced if mode == 'RETURN' else natural)
            r.run_until('process_cpp')
            t.check(kind + ' next natural value', convert(kind, gdb.parse_and_eval(sink)), natural)


@case('HW_R18_FINISH', labels=('research', 'cpp'))
def finish(t):
    exercise(t, 'FINISH', tuple(KINDS))


@case('HW_R18_CALL', labels=('research', 'cpp'))
def call(t):
    exercise(t, 'CALL', tuple(KINDS))


@case('HW_R18_CPP_RETURN', labels=('research', 'cpp'))
def cpp_return(t):
    exercise(t, 'RETURN', ('INT', 'FLOAT'))


@case('HW_R18_SMALL_RETURN', labels=('research', 'cpp'))
def small_return(t):
    exercise(t, 'RETURN', ('SMALL',))


@case('HW_R18_PAIR_RETURN', labels=('research', 'cpp'))
def pair_return(t):
    exercise(t, 'RETURN', ('PAIR',))


@case('HW_R18_HFA_RETURN', labels=('research', 'cpp'))
def hfa_return(t):
    exercise(t, 'RETURN', ('HFA',))
