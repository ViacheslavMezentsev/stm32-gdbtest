"""R7: bounded hardware watchpoint characterization and recovery."""
import gdb
import os
from pathlib import Path
from stm32_gdbtest import case
from lab.session import Research


def setup(t):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set debug remote on')
    sample = gdb.lookup_global_symbol('sample').value()
    return Research(t, (int(sample.address), int(sample.type.sizeof)))


def attempt(r):
    r.last_stop = None
    logfile = Path(os.environ['STM32_GDBTEST_RUN']).parent / ('watch-insert-%d.log' % len(r.evidence))
    gdb.execute('set logging file ' + logfile.as_posix())
    gdb.execute('set logging overwrite on')
    gdb.execute('set logging enabled on')
    failure = None
    try:
        gdb.execute('continue')
    except gdb.error as exc:
        failure = exc
    finally:
        gdb.execute('set logging enabled off')
    if failure is not None:
        diagnostics = [line for line in logfile.read_text(encoding='utf-8', errors='replace').splitlines()
                       if line.startswith('Could not insert hardware watchpoint ')]
        if not diagnostics:
            raise failure
        return {'outcome': 'insertion_rejected', 'message': str(failure), 'diagnostics': diagnostics}
    return {'outcome': 'stopped', 'event': dict(r.last_stop or {})}


def point(r, expression, access):
    bp = gdb.Breakpoint(expression, type=gdb.BP_WATCHPOINT, wp_class=access)
    r.owned.append(bp)
    return bp


def control(t, r):
    t.boot(t.profile['reset_halt'])
    bp = point(r, 'cycles', gdb.WP_WRITE)
    result = attempt(r)
    r.record('recovery', result)
    t.check('control uses hardware', bp.type, gdb.BP_HARDWARE_WATCHPOINT)
    t.check('control stops after rejection or trial', result['outcome'], 'stopped')
    t.check('control watchpoint identity', bp.number in result['event'].get('breakpoints', []), True)
    t.check('control first completed cycle', int(gdb.parse_and_eval('cycles')), 1)
    bp.delete()


@case('HW_R7_WIDTH', labels=('research', 'watch'))
def width(t):
    with setup(t) as r:
        base = int(gdb.parse_and_eval('&sample.bytes[0]'))
        r.record('layout', {'sample': r.ram[0], 'sample_size': r.ram[1], 'bytes': base})
        for size, offset in ((1, 0), (2, 0), (4, 0), (8, 0), (2, 1), (4, 1)):
            t.boot(t.profile['reset_halt'])
            r.run_until('sum_bytes')
            address = (base // size) * size + offset
            t.check('range stays in sample', r.ram[0] <= address and address + size <= sum(r.ram), True)
            t.check('range overlaps bytes read by CPU', address < base + 8 and address + size > base, True)
            expression = '*(uint8_t (*)[%d])%s' % (size, hex(address))
            bp = point(r, expression, gdb.WP_READ)
            t.check('hardware read point', bp.type, gdb.BP_READ_WATCHPOINT)
            sentinel = r.breakpoint('process_sample')
            result = attempt(r)
            result.update(size=size, offset=offset, address=address)
            r.record('range_' + str(size) + '_' + str(offset), result)
            if result['outcome'] == 'stopped':
                t.check('range watchpoint identity', bp.number in result['event'].get('breakpoints', []), True)
                t.check('range accessed inside sum', gdb.newest_frame().name(), 'sum_bytes')
            elif size == 1:
                t.check('one-byte baseline must work', False, True)
            bp.delete()
            sentinel.delete()
        control(t, r)


@case('HW_R7_CAPACITY', labels=('research', 'watch'))
def capacity(t):
    with setup(t) as r:
        base, length = r.ram
        t.check('bounded static words available', base % 4 == 0 and length >= 32, True)
        supported = 0
        for count in range(1, 9):
            t.boot(t.profile['reset_halt'])
            r.run_until('sum_bytes')
            points = [point(r, '*(uint32_t*)' + hex(base + 4 * index), gdb.WP_WRITE)
                      for index in range(count)]
            t.check('all points hardware', all(bp.type == gdb.BP_HARDWARE_WATCHPOINT for bp in points), True)
            sentinel = r.breakpoint('process_sample')
            result = attempt(r)
            result['count'] = count
            r.record('capacity_' + str(count), result)
            if result['outcome'] == 'stopped':
                t.check('static words not written by CPU', sentinel.number in result['event'].get('breakpoints', []), True)
                supported = count
            for bp in points:
                bp.delete()
            sentinel.delete()
            if result['outcome'] == 'insertion_rejected':
                break
        t.check('finite insertion boundary observed', 0 < supported < 8, True)
        r.record('supported_word_points', supported)
        control(t, r)
