"""R8: physical code-point capacity, guard ownership and finish headroom."""
import os
from pathlib import Path
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


def guards():
    return {bp.number: tuple(int(loc.address) for loc in bp.locations)
            for bp in (gdb.breakpoints() or ()) if bp.is_valid() and bp.enabled
            and bp.type == gdb.BP_HARDWARE_BREAKPOINT}


def attempt(r):
    logfile = Path(os.environ['STM32_GDBTEST_RUN']).parent / ('code-insert-%d.log' % len(r.evidence))
    gdb.execute('set logging file ' + logfile.as_posix())
    gdb.execute('set logging overwrite on')
    gdb.execute('set logging enabled on')
    failure = None
    r.last_stop = None
    try:
        gdb.execute('continue')
    except gdb.error as exc:
        failure = exc
    finally:
        gdb.execute('set logging enabled off')
    if failure is not None:
        lines = logfile.read_text(encoding='utf-8', errors='replace').splitlines()
        diagnostics = [line for line in lines if 'Cannot insert hardware breakpoint' in line
                       or line.startswith('Could not insert hardware breakpoints:')]
        if not diagnostics:
            raise failure
        return {'outcome': 'insertion_rejected', 'message': str(failure), 'diagnostics': diagnostics}
    return {'outcome': 'stopped', 'event': dict(r.last_stop or {})}


@case('HW_R8_CAPACITY', labels=('research', 'breakpoints'))
def capacity(t):
    with setup(t) as r:
        names = ('process_sample', 'Default_Handler', 'Reset_Handler', 'read_packet', 'calculate_gain')
        supported = 0
        for count in range(1, len(names) + 1):
            t.boot(t.profile['reset_halt'])
            original = guards()
            t.check('four fault guards present', len(original), 4)
            points = []
            for name in names[:count]:
                # Deliberately bypass the consumer's conservative budget to probe insertion.
                bp = gdb.Breakpoint(name, type=gdb.BP_HARDWARE_BREAKPOINT)
                points.append(bp)
                r.owned.append(bp)
            addresses = [int(bp.locations[0].address) for bp in points]
            t.check('distinct point addresses', len(set(addresses)), count)
            t.check('no overlap with guards', any(a in group for a in addresses for group in original.values()), False)
            result = attempt(r)
            r.record('count_' + str(count), dict(result, added=count, guards=len(original), addresses=addresses))
            if result['outcome'] == 'stopped':
                t.check('expected first function', points[0].number in result['event'].get('breakpoints', []), True)
                supported = count
            for bp in points:
                bp.delete()
            t.check('fault guards unchanged', guards(), original)
            if result['outcome'] == 'insertion_rejected':
                break
        t.check('bounded physical limit observed', 0 < supported < len(names), True)
        r.record('capacity', {'guard_points': 4, 'extra_points': supported, 'total': supported + 4})
        # No reset here: release only owned points and prove current-session continuation.
        r.run_until('process_sample')
        t.check('control function after release', gdb.newest_frame().name(), 'process_sample')


@case('HW_R8_FINISH', labels=('research', 'breakpoints'))
def finish_headroom(t):
    with setup(t) as r:
        r.run_until('sum_bytes')
        original = guards()
        t.check('four guards at function entry', len(original), 4)
        fillers = [r.breakpoint(name) for name in ('Default_Handler', 'Reset_Handler')]
        finish = gdb.FinishBreakpoint(gdb.newest_frame(), internal=True)
        r.owned.append(finish)
        finish_number = finish.number
        result = attempt(r)
        r.record('full_budget_finish', result)
        t.check('finish insertion needs headroom', result['outcome'], 'insertion_rejected')
        t.check('failed insertion leaves current frame', gdb.newest_frame().name(), 'sum_bytes')
        fillers[0].delete()
        result = attempt(r)
        r.record('released_one_finish', result)
        t.check('finish resumes after freeing one point', result['outcome'], 'stopped')
        t.check('finish stop identity', finish_number in result['event'].get('breakpoints', []), True)
        t.check('finish object invalid after firing', finish.is_valid(), False)
        t.check('natural return retained', int(finish.return_value), 773)
        fillers[1].delete()
        t.check('only original guards remain', guards(), original)
        r.run_until('process_sample')
        t.check('caller consumed natural value', int(gdb.parse_and_eval('checksum')), 773 ^ 0xffffff85)
