"""R3: stop actions, target-counter deadlines and same-value writes."""
import gdb
from stm32_gdbtest import case
from lab.session import Research
from lab.commands import execute_sequence


def lab(t):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set debug remote on')
    value = gdb.lookup_global_symbol('sample').value()
    return Research(t, (int(value.address), int(value.type.sizeof)))


def resume(t, r, expected):
    number = expected.number
    r.last_stop = None
    gdb.execute('continue')
    stop = dict(r.last_stop or {})
    r.record('event_' + str(len(r.evidence)), stop)
    t.check('expected stop identity', number in stop.get('breakpoints', []), True)
    return stop


@case('HW_R3_COMMANDS', labels=('research', 'automation'))
def command_actions(t):
    with lab(t) as r:
        gdb.execute('set $intercepts = 0')
        gdb.execute('set $after_continue = 0')
        intercept = r.breakpoint('sum_bytes')
        intercept.condition = 'seed == 3'
        intercept.commands = ('silent\nset $intercepts = $intercepts + 1\n'
                              'return 100\ncontinue\nset $after_continue = 1\n')
        sentinel = r.breakpoint('process_sample')
        sentinel.condition = 'sequence == 1'
        resume(t, r, sentinel)
        t.check('one intercepted call', int(gdb.convenience_variable('intercepts')), 1)
        t.check('commands after continue ignored', int(gdb.convenience_variable('after_continue')), 0)
        t.check('caller consumed command-list return', int(gdb.parse_and_eval('checksum')), 100 ^ 0xffffff85)
        intercept.delete()
        sentinel.delete()
        r.run_until('process_sample')
        t.check('subsequent natural call restored', int(gdb.parse_and_eval('checksum')), 774 ^ 0xffffff85)


@case('HW_R3_DEADLINE', labels=('research', 'automation'))
def counter_deadline(t):
    # Cycles are application progress, not milliseconds or wall time.
    with lab(t) as r:
        for start in (0, 0xfffffffe):
            t.boot(t.profile['reset_halt'])
            t.set_value('cycles', start)
            gdb.set_convenience_variable('start', gdb.Value(start).cast(gdb.lookup_type('unsigned int')))
            expression = '(unsigned int)(cycles - $start) >= 3'
            t.check('deadline initially false', bool(gdb.parse_and_eval(expression)), False)
            wp = gdb.Breakpoint(expression, type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_WRITE)
            r.owned.append(wp)
            t.check('predicate uses hardware watchpoint', wp.type, gdb.BP_HARDWARE_WATCHPOINT)
            resume(t, r, wp)
            t.check('three completed cycles', int(gdb.parse_and_eval('cycles')), (start + 3) & 0xffffffff)
            t.check('deadline predicate true', bool(gdb.parse_and_eval(expression)), True)
            r.record('deadline_' + str(start), {'start': start, 'end': int(gdb.parse_and_eval('cycles')),
                                  'units': 'completed application cycles'})
            wp.delete()


@case('HW_R3_SAMEVALUE', labels=('research', 'automation'))
def same_value_store(t):
    with lab(t) as r:
        for access in (gdb.WP_WRITE, gdb.WP_ACCESS):
            t.boot(t.profile['reset_halt'])
            r.run_until('process_sample')
            r.run_until('process_sample')
            t.check('one completed cycle', int(gdb.parse_and_eval('cycles')), 1)
            before = int(gdb.parse_and_eval('checksum'))
            # Repeat the first computation: the natural CPU store will write the same checksum.
            t.set_value('sequence', 0)
            wp = gdb.Breakpoint('checksum', type=gdb.BP_WATCHPOINT, wp_class=access)
            r.owned.append(wp)
            t.check('hardware data point', wp.type,
                    gdb.BP_HARDWARE_WATCHPOINT if access == gdb.WP_WRITE else gdb.BP_ACCESS_WATCHPOINT)
            sentinel = r.breakpoint('process_sample')
            stop = resume(t, r, sentinel if access == gdb.WP_WRITE else wp)
            t.check('same checksum after CPU store', int(gdb.parse_and_eval('checksum')), before)
            if access == gdb.WP_WRITE:
                t.check('same-value watch did not report a hit', wp.number in stop['breakpoints'], False)
                t.check('sentinel reached after completion', int(gdb.parse_and_eval('cycles')), 2)
            else:
                t.check('access stops before cycle increment', int(gdb.parse_and_eval('cycles')), 1)
            r.record('same_value_' + str(access), {'access': access, 'value': before, 'stop': stop})
            wp.delete()
            sentinel.delete()


@case('HW_R3_LANGUAGE', labels=('research', 'automation'))
def command_language(t):
    with lab(t) as r:
        r.run_until('process_sample')
        gdb.execute('macro define RESEARCH_WIDTH 8')
        t.check('macro in current source context', int(gdb.parse_and_eval('RESEARCH_WIDTH == sizeof(input->bytes)')), 1)
        gdb.execute('define research_classify\nif $arg0 > 2\nset $result = 1\nelse\nset $result = 0\nend\nend')
        execute_sequence(gdb.execute, ['research_classify 3', 'set $saved = $result'])
        t.check('parameterized branch true', int(gdb.convenience_variable('saved')), 1)
        gdb.execute('research_classify 1')
        t.check('parameterized branch false', int(gdb.convenience_variable('result')), 0)
        output = execute_sequence(gdb.execute, ['printf "left;right\\n"'])
        t.check('quoted semicolon preserved', output, ['left;right\n'])
        gdb.execute('set $later = 0')
        try:
            execute_sequence(gdb.execute, ['research_missing_command', 'set $later = 1'])
        except gdb.error as exc:
            r.record('command_error', str(exc))
        else:
            t.check('unknown command must fail', False, True)
        t.check('later command not executed', int(gdb.convenience_variable('later')), 0)
