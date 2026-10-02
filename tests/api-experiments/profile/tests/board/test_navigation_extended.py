"""R16: source/address navigation, frame exits and interrupted nexti."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


def setup(t):
    for command in ('monitor gdb_breakpoint_override hard', 'monitor debug_level 3',
                    'set breakpoint auto-hw on', 'set displaced-stepping off', 'set debug remote on'):
        gdb.execute(command)
    value = gdb.lookup_global_symbol('sample').value()
    return Research(t, (int(value.address), int(value.type.sizeof)))


def command(r, text, label):
    r.last_stop = None
    gdb.execute(text)
    frame = gdb.newest_frame()
    sal = frame.find_sal()
    r.record(label, dict(command=text, event=r.last_stop, pc=int(frame.pc()),
                         function=frame.name(), line=sal.line, frames=r.frames()))


def source_pc(t, spec):
    tail, locations = gdb.decode_line(spec)
    t.check('complete source specification', tail, None)
    t.check('unique source location', len(locations), 1)
    return int(locations[0].pc)


def call_site(t):
    block = gdb.block_for_pc(t.value('(unsigned int)process_sample') & ~1)
    while block.function is None:
        block = block.superblock
    instructions = gdb.newest_frame().architecture().disassemble(block.start, block.end)
    calls = [(i, ins) for i, ins in enumerate(instructions)
             if ins['asm'].split()[0] == 'bl' and '<sum_bytes>' in ins['asm']]
    t.check('unique natural call instruction', len(calls), 1)
    index, instruction = calls[0]
    return instruction['addr'], instructions[index + 1]['addr']


def consumed(t, r):
    r.run_until('process_packet')
    t.check('caller consumed natural sum', t.value('checksum'), 773 ^ 0xffffff85)
    t.check('still first main iteration', t.value('cycles'), 0)


@case('HW_R16_UNTIL', labels=('research', 'navigation'))
def until(t):
    with setup(t) as r:
        body = source_pc(t, 'app.c:26')
        end = source_pc(t, 'app.c:28')
        r.run_until('*' + hex(body))
        t.check('first loop body', t.value('i'), 0)
        command(r, 'until app.c:28', 'until_return_line')
        t.check('until reached exact return PC', int(gdb.newest_frame().pc()), end)
        t.check('until retained frame', gdb.newest_frame().name(), 'sum_bytes')
        t.check('whole loop consumed', t.value('total'), 773)
        symbol, _ = gdb.lookup_symbol('i', gdb.newest_frame().block())
        t.check('loop index out of scope after loop', symbol is None, True)
        r.record('scope', dict(name='i', state='out_of_scope', result=t.value('total')))
        consumed(t, r)


@case('HW_R16_ADVANCE', labels=('research', 'navigation'))
def advance(t):
    with setup(t) as r:
        r.run_until('process_sample')
        body = source_pc(t, 'app.c:26')
        _, return_pc = call_site(t)
        command(r, 'advance app.c:26', 'advance_into_child')
        t.check('advance enters child', gdb.newest_frame().name(), 'sum_bytes')
        t.check('advance exact source PC', int(gdb.newest_frame().pc()), body)
        destination = t.value('(unsigned int)process_packet') & ~1
        command(r, 'advance *' + hex(destination), 'advance_frame_exit')
        t.check('advance stopped at current frame exit', gdb.newest_frame().name(), 'process_sample')
        t.check('advance did not reach requested target', int(gdb.newest_frame().pc()) != destination, True)
        t.check('advance stopped after natural call', int(gdb.newest_frame().pc()), return_pc)
        t.check('sum result at frame exit', t.value('$r0'), 773)
        consumed(t, r)


def over_call(t, interrupted):
    with setup(t) as r:
        r.run_until('process_sample')
        call, after = call_site(t)
        r.run_until('*' + hex(call))
        if interrupted:
            foreign = r.breakpoint('sum_bytes')
            number = foreign.number
        command(r, 'nexti', 'nexti_stop')
        if interrupted:
            t.check('foreign breakpoint identified', (r.last_stop or {}).get('breakpoints'), [number])
            t.check('nexti interrupted inside callee', gdb.newest_frame().name(), 'sum_bytes')
            t.check('nexti target not reached', int(gdb.newest_frame().pc()) != after, True)
            foreign.delete()
            r.run_until('*' + hex(after))
        t.check('call stepped over at exact instruction', int(gdb.newest_frame().pc()), after)
        t.check('natural caller selected', gdb.newest_frame().name(), 'process_sample')
        t.check('natural return register', t.value('$r0'), 773)
        consumed(t, r)


@case('HW_R16_NEXTI', labels=('research', 'navigation'))
def nexti(t):
    over_call(t, False)


@case('HW_R16_INTERRUPT', labels=('research', 'navigation'))
def interrupted(t):
    over_call(t, True)
