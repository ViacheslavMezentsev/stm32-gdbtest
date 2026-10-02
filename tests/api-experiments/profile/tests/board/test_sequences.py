"""R14: finite interception scripts over natural main-loop calls, not dummy calls."""
import gdb
from stm32_gdbtest import case
from lab.session import Research
from lab.sequence import CallOrder


def exercise(t, statuses, reject_order=False):
    for command in ('monitor gdb_breakpoint_override hard', 'monitor debug_level 3',
                    'set breakpoint auto-hw on', 'set displaced-stepping off', 'set debug remote on'):
        gdb.execute(command)
    packet = gdb.lookup_global_symbol('packet').value()
    address, size = int(packet.address), int(packet.type.sizeof)
    with Research(t, (address, size)) as r:
        points = {name: r.breakpoint(name) for name in ('process_packet', 'read_packet')}
        order = CallOrder(('process_packet', 'read_packet') * len(statuses) + ('process_packet',))
        events = []

        def advance():
            gdb.execute('continue')
            stop = r.last_stop or {}
            matches = [name for name, bp in points.items() if bp.number in stop.get('breakpoints', ())
                       and int(gdb.newest_frame().pc()) == int(bp.locations[0].address)]
            if len(matches) != 1 or len(stop.get('breakpoints', ())) != 1:
                raise RuntimeError('Unexpected sequence stop: ' + repr(stop))
            name = matches[0]
            events.append(dict(name=name, cycle=t.value('cycles'), pc=int(gdb.newest_frame().pc())))
            r.record('event_' + str(len(events)), events[-1])
            order.observe(name)

        accepted = 0
        prior_status = None
        prior_data = None
        start_cycle = None
        for index, status in enumerate(statuses):
            advance()
            if start_cycle is None:
                start_cycle = t.value('cycles')
            t.check('exact iteration', t.value('cycles'), start_cycle + index)
            if prior_status is not None:
                t.check('previous status consumed', t.value('packet_status'), prior_status)
                t.check('last accepted total retained', t.value('packet_total'), accepted)
                t.check('previous bytes retained', list(r.read_memory(output, 8)), list(prior_data))
            advance()
            frame = gdb.newest_frame()
            t.check('natural caller', frame.older().name(), 'process_packet')
            output = int(frame.read_var('output'))
            t.check('output pointer', output, t.value('(unsigned int)&packet.data[0]'))
            t.check('output capacity', int(frame.read_var('capacity')), 8)
            if reject_order:
                wrong = CallOrder(('process_packet',))
                try:
                    wrong.observe(events[-1]['name'])
                except ValueError as exc:
                    t.check('specific order mismatch', str(exc),
                            'Call order at 0: expected process_packet, observed read_packet')
                    t.check('mismatch did not consume expectation', wrong.position, 0)
                    r.record('expected_rejection', dict(error=str(exc), frames=r.frames()))
                else:
                    raise RuntimeError('Order mismatch was accepted')
            if status is not None:
                data = bytes(range(index + 1, index + 9))
                r.record('action_' + str(index), dict(status=status, data=list(data), output=output))
                r._range(output, len(data))
                gdb.selected_inferior().write_memory(output, data)
                gdb.execute('return ' + str(status))
                t.check('forced return selected caller', gdb.newest_frame().name(), 'process_packet')
            else:
                data = bytes([0, 1, 2, 3, 127, 128, 254, 255])
            prior_status = 8 if status is None else status
            prior_data = data
            if prior_status == 8:
                accepted = sum(data)
        advance()
        order.complete()
        t.check('exact final iteration', t.value('cycles'), start_cycle + len(statuses))
        t.check('final status consumed', t.value('packet_status'), prior_status)
        t.check('final accepted total', t.value('packet_total'), accepted)
        t.check('final output data', list(r.read_memory(output, 8)), list(prior_data))
        t.check('packet prefix intact', t.value('packet.format'), 1)
        t.check('packet suffix intact', t.value('packet.destination'), 7)
        r.record('sequence_complete', dict(events=len(events), actions=list(statuses), total=accepted))
        r.clear()
        r.run_until('process_packet')
        t.check('natural status after removal', t.value('packet_status'), 8)
        t.check('natural total after removal', t.value('packet_total'), 770)


@case('HW_R14_SEQUENCE', labels=('research', 'sequence'))
def sequence(t):
    exercise(t, (-5, -5, 8, None))


@case('HW_R14_RETAIN', labels=('research', 'sequence'))
def retain(t):
    exercise(t, (8, -5, 3, None))


@case('HW_R14_ORDER', labels=('research', 'sequence'))
def order(t):
    exercise(t, (None,), reject_order=True)
