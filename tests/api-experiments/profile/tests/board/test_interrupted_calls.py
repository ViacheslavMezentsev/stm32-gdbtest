"""R9: breakpoint-interrupted dummy calls and nested status substitution."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


def setup(t):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set displaced-stepping off')
    gdb.execute('set debug remote on')
    sample = gdb.lookup_global_symbol('sample').value()
    return Research(t, (int(sample.address), int(sample.type.sizeof)))


def context():
    frame = gdb.newest_frame()
    return {name: int(frame.read_register(name)) for name in
            ('pc', 'sp', 'lr', 'r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7', 'r8', 'r9', 'r10', 'r11', 'r12')}


def interrupt(t, r, expression, location):
    bp = r.breakpoint(location)
    number = bp.number
    before = context()
    failure = None
    r.last_stop = None
    try:
        gdb.parse_and_eval(expression)
    except gdb.error as exc:
        failure = str(exc)
    frames = r.frames()
    stop = dict(r.last_stop or {})
    r.record('interrupted', dict(expression=expression, error=failure, frames=frames, event=stop))
    t.check('expression reports interruption', failure is not None, True)
    t.check('owned breakpoint identifies interruption', number in stop.get('breakpoints', []), True)
    t.check('expected called function', gdb.newest_frame().name(), location)
    t.check('one dummy frame visible', sum(f['type'] == gdb.DUMMY_FRAME for f in frames), 1)
    bp.delete()
    return before


def resume(t, r, before):
    r.last_stop = None
    gdb.execute('continue')
    after = context()
    frames = r.frames()
    r.record('resumed', dict(before=before, after=after, frames=frames, event=r.last_stop))
    t.check('dummy call restored registers', after, before)
    t.check('dummy frame gone', any(f['type'] == gdb.DUMMY_FRAME for f in frames), False)
    t.check('original frame selected', gdb.newest_frame().name(), 'process_sample')


@case('HW_R9_RESUME', labels=('research', 'calls'))
def resume_call(t):
    with setup(t) as r:
        r.run_until('process_sample')
        memory = r.read_memory(*r.ram)
        before = interrupt(t, r, 'sum_bytes(sample.bytes, 8, 5)', 'sum_bytes')
        t.check('dummy call argument', int(gdb.parse_and_eval('seed')), 5)
        resume(t, r, before)
        t.check('input preserved', r.read_memory(*r.ram).hex(), memory.hex())
        # The interrupted Python expression is abandoned; do not invent its return value.
        value = gdb.parse_and_eval('sum_bytes(sample.bytes, 8, 5)')
        t.check('fresh uninterrupted call returns a value', int(value), 775)
        r.run_until('process_sample')
        t.check('natural execution remains correct', int(gdb.parse_and_eval('checksum')), 773 ^ 0xffffff85)


@case('HW_R9_INTERCEPT', labels=('research', 'calls'))
def intercept_call(t):
    with setup(t) as r:
        r.run_until('process_sample')
        packet_before = bytes(gdb.selected_inferior().read_memory(
            int(gdb.parse_and_eval('&packet')), int(gdb.parse_and_eval('sizeof(packet)'))))
        total_before = int(gdb.parse_and_eval('packet_total'))
        before = interrupt(t, r, 'process_packet()', 'read_packet')
        t.check('nested natural caller', gdb.newest_frame().older().name(), 'process_packet')
        t.force_return('-7')
        t.check('forced return selects caller inside dummy call', gdb.newest_frame().name(), 'process_packet')
        resume(t, r, before)
        t.check('nested caller consumed error', int(gdb.parse_and_eval('packet_status')), -7)
        t.check('error branch preserved total', int(gdb.parse_and_eval('packet_total')), total_before)
        t.check('packet untouched on forced error', bytes(gdb.selected_inferior().read_memory(
            int(gdb.parse_and_eval('&packet')), len(packet_before))).hex(), packet_before.hex())
        r.record('side_effect', {'packet_status': -7, 'packet_total': total_before})
        # Restoring dummy registers does not roll back RAM; the next normal call repairs the sink.
        gdb.parse_and_eval('process_packet()')
        t.check('normal call replaces error status', int(gdb.parse_and_eval('packet_status')), 8)
        t.check('normal call copies and sums payload', int(gdb.parse_and_eval('packet_total')), 770)
        r.run_until('process_sample')
        t.check('natural caller still correct', int(gdb.parse_and_eval('checksum')), 773 ^ 0xffffff85)
