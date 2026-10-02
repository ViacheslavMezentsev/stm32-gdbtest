"""R6: caller-aware selection and recursive frame identity."""
import gdb
from stm32_gdbtest import case
from lab.session import Research
from lab.navigation import caller_is


def setup(t):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set displaced-stepping off')
    gdb.execute('set debug remote on')
    value = gdb.lookup_global_symbol('sample').value()
    return Research(t, (int(value.address), int(value.type.sizeof)))


def resume(t, r, bp):
    number = bp.number
    r.last_stop = None
    gdb.execute('continue')
    r.record('event_' + str(len(r.evidence)), dict(r.last_stop or {}))
    t.check('expected point identity', number in (r.last_stop or {}).get('breakpoints', []), True)


def verify_cycle(t, r, beta=238):
    r.run_until('process_routes')
    t.check('alpha unchanged', int(gdb.parse_and_eval('route_a_result')), 124)
    t.check('beta result', int(gdb.parse_and_eval('route_b_result')), beta)
    r.run_until('process_routes')
    t.check('next alpha natural', int(gdb.parse_and_eval('route_a_result')), 124)
    t.check('next beta natural', int(gdb.parse_and_eval('route_b_result')), 238)


@case('HW_R6_CONTEXT', labels=('research', 'stack'))
def context(t):
    with setup(t) as r:
        visits = []

        class SelectedCall(gdb.Breakpoint):
            def stop(self):
                # Read-only GDB operations. Never resume, delete points or select frames here.
                frame = gdb.newest_frame()
                names = []
                cursor = frame
                while cursor and len(names) < 8:
                    names.append(cursor.name())
                    cursor = cursor.older()
                depth = int(frame.read_var('depth'))
                selected = depth == 1 and caller_is(frame, 'route_beta', 3)
                visits.append({'stack': names, 'depth': depth, 'seed': int(frame.read_var('seed')), 'selected': selected})
                return selected

        bp = SelectedCall('walk_route', type=gdb.BP_HARDWARE_BREAKPOINT)
        r.owned.append(bp)
        resume(t, r, bp)
        r.record('visits', visits)
        t.check('all calls before selected context', [v['depth'] for v in visits], [2, 1, 0, 3, 2, 1])
        t.check('only desired call selected', [v['selected'] for v in visits], [False] * 5 + [True])
        t.check('distinct arguments at equal depth', [v['seed'] for v in visits if v['depth'] == 1], [11, 22])
        t.check('native caller function agrees', bool(gdb.parse_and_eval('$_caller_is("route_beta", 3)')), True)
        t.check('wrong caller depth rejected', caller_is(gdb.newest_frame(), 'route_beta', 2), False)
        bp.delete()
        verify_cycle(t, r)


@case('HW_R6_FINISH', labels=('research', 'stack'))
def recursive_finish(t):
    with setup(t) as r:
        bp = r.breakpoint('walk_route')
        bp.condition = 'depth == 2 && $_caller_is("route_beta", 2)'
        resume(t, r, bp)
        bp.delete()
        frame = gdb.newest_frame()
        t.check('selected recursive argument', int(frame.read_var('seed')), 12)
        expected_pc = int(frame.older().pc())
        expected_sp = int(frame.older().read_register('sp'))
        finish = gdb.FinishBreakpoint(frame, internal=True)
        r.owned.append(finish)
        resume(t, r, finish)
        value = int(finish.return_value)
        r.record('return_value', value)
        t.check('selected depth2 return', value, 35)
        frame = gdb.newest_frame()
        t.check('recursive caller name', frame.name(), 'walk_route')
        t.check('recursive caller depth', int(frame.read_var('depth')), 3)
        t.check('recursive caller seed', int(frame.read_var('seed')), 2)
        t.check('caller return PC', int(frame.pc()), expected_pc)
        t.check('caller stack pointer', int(frame.read_register('sp')), expected_sp)
        verify_cycle(t, r)


@case('HW_R6_RETURN', labels=('research', 'stack'))
def recursive_return(t):
    with setup(t) as r:
        bp = r.breakpoint('walk_route')
        bp.condition = 'depth == 1 && $_caller_is("route_beta", 3)'
        resume(t, r, bp)
        bp.delete()
        t.check('selected recursive seed', int(gdb.newest_frame().read_var('seed')), 22)
        gdb.execute('return 100')
        t.check('remaining caller depth', int(gdb.newest_frame().read_var('depth')), 2)
        # Remaining additions: depth2 + depth3 + route_beta offset.
        verify_cycle(t, r, beta=305)
