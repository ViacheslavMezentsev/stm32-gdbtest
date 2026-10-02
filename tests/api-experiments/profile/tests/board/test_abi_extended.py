"""R17: scalar ABI matrix on the ordinary mixed-type calculation application."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


KINDS = (
    ('VOID', 'accumulate', '3', None, None, ''),
    ('DOUBLE', 'affine', '2.5, 0.5', 'accepted_double', 5.5, '(double)-2.25'),
    ('FLOAT', 'gain_adjust', '(float)3.5', 'accepted_float', 4.75, '(float)-2.5'),
    ('STACK', 'weighted_sum', '1, 2, 3, 4, 5, 6', 'accepted_stack', 654321, '(uint32_t)42'),
)


def scalar(kind, value):
    return float(value) if kind in ('DOUBLE', 'FLOAT') else int(value)


def exercise(t, mode):
    for command in ('monitor gdb_breakpoint_override hard', 'monitor debug_level 3',
                    'set breakpoint auto-hw on', 'set displaced-stepping off', 'set debug remote on'):
        gdb.execute(command)
    value = gdb.lookup_global_symbol('accumulated').value()
    with Research(t, (int(value.address), 4)) as r:
        r.record('mode', mode)
        for kind, fn, args, sink, natural, replacement in KINDS:
            if mode == 'CALL':
                r.run_until('process_abi')
                frame = gdb.newest_frame()
                before = dict(pc=int(frame.pc()), sp=int(frame.read_register('sp')))
                counter = t.value('accumulated')
                result = gdb.parse_and_eval(fn + '(' + args + ')')
                if kind == 'VOID':
                    t.check('direct void type', result.type.code, gdb.TYPE_CODE_VOID)
                    t.check('direct void effect', t.value('accumulated'), counter + 3)
                    actual = None
                else:
                    actual = scalar(kind, result)
                    t.check(kind + ' direct result', actual, natural)
                frame = gdb.newest_frame()
                t.check(kind + ' direct PC SP restored', dict(pc=int(frame.pc()),
                        sp=int(frame.read_register('sp'))), before)
                r.record(kind.lower() + '_direct', dict(result=actual, before=before,
                                                       cpacr=t.value('*(unsigned int*)0xe000ed88')))
            else:
                r.run_until('*' + hex(t.value('(unsigned int)' + fn) & ~1))
                frame = gdb.newest_frame()
                t.check(kind + ' natural caller', frame.older().name(), 'process_abi')
                counter = t.value('accumulated')
                if kind == 'STACK':
                    arguments = [int(frame.read_var(name)) for name in 'abcdef']
                    sp = int(frame.read_register('sp'))
                    memory = bytes(gdb.selected_inferior().read_memory(sp, 8))
                    stacked = [int.from_bytes(memory[i:i + 4], 'little') for i in (0, 4)]
                    t.check('six source arguments', arguments, [1, 2, 3, 4, 5, 6])
                    t.check('stack aligned at callee entry', sp % 8, 0)
                    t.check('fifth and sixth arguments on stack', stacked, [5, 6])
                    r.record('stack_arguments', dict(values=arguments, sp=sp, stacked=stacked))
                if mode == 'FINISH':
                    bp = gdb.FinishBreakpoint(frame, internal=True)
                    r.owned.append(bp)
                    number = bp.number
                    gdb.execute('continue')
                    t.check(kind + ' finish identity', number in (r.last_stop or {}).get('breakpoints', []), True)
                    result = bp.return_value
                    if kind == 'VOID':
                        t.check('void has no scalar return', result is None or result.type.code == gdb.TYPE_CODE_VOID, True)
                        actual = None
                    else:
                        t.check(kind + ' return captured', result is not None, True)
                        actual = scalar(kind, result)
                        t.check(kind + ' captured result', actual, natural)
                    r.record(kind.lower() + '_finish', dict(result=actual, event=r.last_stop))
                else:
                    gdb.execute('return ' + replacement)
                t.check(kind + ' caller after return', gdb.newest_frame().name(), 'process_abi')
            r.run_until('process_abi')
            if kind == 'VOID':
                expected = counter + (6 if mode == 'CALL' else 3 if mode == 'FINISH' else 0)
                t.check('void caller side effect', t.value('accumulated'), expected)
                r.record('void_effect', dict(before=counter, after=t.value('accumulated')))
            else:
                expected = {'DOUBLE': -2.25, 'FLOAT': -2.5, 'STACK': 42}[kind] if mode == 'RETURN' else natural
                actual = scalar(kind, gdb.parse_and_eval(sink))
                t.check(kind + ' caller consumed result', actual, expected)
                r.record(kind.lower() + '_sink', actual)
            r.run_until('process_abi')
            if kind == 'VOID':
                t.check('next natural void effect', t.value('accumulated'), expected + 3)
            else:
                t.check(kind + ' next natural result', scalar(kind, gdb.parse_and_eval(sink)), natural)


@case('HW_R17_FINISH', labels=('research', 'abi'))
def finish(t):
    exercise(t, 'FINISH')


@case('HW_R17_RETURN', labels=('research', 'abi'))
def forced(t):
    exercise(t, 'RETURN')


@case('HW_R17_CALL', labels=('research', 'abi'))
def call(t):
    exercise(t, 'CALL')
