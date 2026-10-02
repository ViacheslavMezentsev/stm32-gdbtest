"""R15: optimized dual-channel application, inline frames and distinct locations."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


def setup(t):
    for command in ('monitor gdb_breakpoint_override hard', 'monitor debug_level 3',
                    'set breakpoint auto-hw on', 'set displaced-stepping off', 'set debug remote on'):
        gdb.execute(command)
    value = gdb.lookup_global_symbol('iterations').value()
    return Research(t, (int(value.address), 4))


def multiple(t, r):
    before = {bp.number for bp in (gdb.breakpoints() or ())}
    try:
        r.breakpoint('scale_channel')
    except ValueError as exc:
        t.check('adapter rejects multiple locations', str(exc), 'Missing or ambiguous breakpoint location')
        r.record('adapter_rejection', str(exc))
    else:
        raise RuntimeError('Single-location adapter accepted multiple locations')
    t.check('rejected point removed', {bp.number for bp in (gdb.breakpoints() or ())} == before, True)
    used = sum(len(bp.locations) for bp in (gdb.breakpoints() or ())
               if bp.enabled and bp.type == gdb.BP_HARDWARE_BREAKPOINT)
    bp = gdb.Breakpoint('scale_channel', type=gdb.BP_HARDWARE_BREAKPOINT)
    r.owned.append(bp)
    addresses = sorted(int(loc.address) for loc in bp.locations)
    t.check('two distinct inline locations', len(set(addresses)), 2)
    t.check('location budget respected', used + len(addresses) <= t.profile['breakpoint_limit'], True)
    r.record('locations', dict(addresses=addresses, previous_slots=used, required_slots=len(addresses)))
    return bp, addresses


def locals_snapshot(frame):
    values = {}
    for name in ('input', 'multiplier', 'product'):
        value = frame.read_var(name)
        value.fetch_lazy()
        values[name] = dict(optimized_out=value.is_optimized_out,
                            value=None if value.is_optimized_out else int(value))
    return values


@case('HW_R15_LOCATIONS', labels=('research', 'optimized'))
def locations(t):
    with setup(t) as r:
        bp, addresses = multiple(t, r)
        for index, expected in enumerate((addresses[0], addresses[1], addresses[0])):
            gdb.execute('continue')
            t.check('same breakpoint identity', (r.last_stop or {}).get('breakpoints'), [bp.number])
            frame = gdb.newest_frame()
            t.check('location selected by PC', int(frame.pc()), expected)
            t.check('inline frame type', frame.type(), gdb.INLINE_FRAME)
            t.check('containing function', frame.older().name(), 'main')
            values = locals_snapshot(frame)
            t.check('inline input', values['input']['value'], 23 if index == 1 else 11)
            t.check('inline multiplier', values['multiplier']['value'], 3)
            r.record('hit_' + str(index), dict(pc=int(frame.pc()), frames=r.frames(), locals=values))
        t.check('completed one iteration', t.value('iterations'), 1)
        t.check('first channel result', t.value('output_a'), 40)
        t.check('second channel result', t.value('output_b'), 76)


@case('HW_R15_VALUES', labels=('research', 'optimized'))
def values(t):
    with setup(t) as r:
        bp, addresses = multiple(t, r)
        bp.delete()
        r.run_until('*' + hex(addresses[0]))
        frame = gdb.newest_frame()
        initial = locals_snapshot(frame)
        r.record('before_instruction', dict(frames=r.frames(), locals=initial))
        instructions = frame.architecture().disassemble(frame.pc(), count=2)
        t.check('multiplication at inline entry', instructions[0]['asm'].startswith('mul'), True)
        gdb.execute('stepi')
        frame = gdb.newest_frame()
        t.check('one instruction executed', int(frame.pc()), instructions[1]['addr'])
        t.check('still inside inline frame', frame.type(), gdb.INLINE_FRAME)
        after = locals_snapshot(frame)
        r.record('after_instruction', dict(frames=r.frames(), locals=after, instructions=instructions))
        t.check('product available after multiply', after['product']['value'], 33)
        t.check('overwritten input explicitly optimized out', after['input']['optimized_out'], True)
        try:
            r.freeze(frame.read_var('input'))
        except ValueError as exc:
            t.check('snapshot rejects unavailable value', str(exc), 'Optimized-out value')
        else:
            raise RuntimeError('Unavailable value silently accepted')
        r.run_until('*' + hex(addresses[1]))
        t.check('caller consumed first result', t.value('output_a'), 40)
        r.run_until('*' + hex(addresses[0]))
        t.check('natural iteration completed', t.value('iterations'), 1)
        t.check('second result retained', t.value('output_b'), 76)
