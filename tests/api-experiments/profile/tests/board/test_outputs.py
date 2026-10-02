"""R4: natural output parameters and caller-visible return substitution."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


def exercise(t, status=None, payload=None):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set displaced-stepping off')
    gdb.execute('set debug remote on')
    value = gdb.lookup_global_symbol('packet').value()
    address, size = int(value.address), int(value.type.sizeof)
    with Research(t, (address, size)) as r:
        r.run_until('read_packet')
        frame = gdb.newest_frame()
        t.check('natural caller', frame.older().name(), 'process_packet')
        output = int(frame.read_var('output'))
        capacity = int(frame.read_var('capacity'))
        expected_address = int(gdb.parse_and_eval('&packet.data[0]'))
        t.check('output belongs to application packet', output, expected_address)
        t.check('output capacity', capacity, 8)
        before = bytes(gdb.selected_inferior().read_memory(address, size))
        offset = output - address
        t.check('output range inside packet', 0 <= offset and offset + capacity <= size, True)
        if payload is not None:
            t.check('payload fits exact output range', len(payload), capacity)
            r.record('mutation_intent', {'offset': offset, 'before': list(before[offset:offset+capacity]),
                                        'payload': list(payload), 'return': status})
            gdb.selected_inferior().write_memory(output, payload)
            gdb.execute('return ' + str(status))
        else:
            gdb.execute('finish')
        t.check('selected natural caller after return', gdb.newest_frame().name(), 'process_packet')
        # Next entry is after the previous caller has consumed status and data.
        r.run_until('process_packet')
        after = bytes(gdb.selected_inferior().read_memory(address, size))
        expected_data = payload if payload is not None else bytes([0, 1, 2, 3, 127, 128, 254, 255])
        expected_status = 8 if status is None else status
        t.check('caller saved signed status', int(gdb.parse_and_eval('packet_status')), expected_status)
        t.check('output bytes persist', list(after[offset:offset+capacity]), list(expected_data))
        t.check('packet prefix preserved', list(after[:offset]), list(before[:offset]))
        t.check('packet suffix preserved', list(after[offset+capacity:]), list(before[offset+capacity:]))
        t.check('caller accepted only full packet', int(gdb.parse_and_eval('packet_total')),
                sum(expected_data) if expected_status == 8 else 0)
        r.record('result', {'status': expected_status, 'data': list(expected_data),
                            'accepted_total': int(gdb.parse_and_eval('packet_total'))})
        # Removing interception must restore ordinary application behavior.
        r.run_until('process_packet')
        t.check('following natural status', int(gdb.parse_and_eval('packet_status')), 8)
        t.check('following natural total', int(gdb.parse_and_eval('packet_total')), 770)


@case('HW_R4_NATURAL', labels=('research', 'outputs'))
def natural(t):
    exercise(t)


@case('HW_R4_OUTPUT', labels=('research', 'outputs'))
def output(t):
    exercise(t, 8, bytes(range(1, 9)))


@case('HW_R4_ERROR', labels=('research', 'outputs'))
def error(t):
    exercise(t, -5, bytes([0xa5] * 8))


@case('HW_R4_SHORT', labels=('research', 'outputs'))
def short(t):
    exercise(t, 3, bytes([10, 20, 30, 0xa5, 0xa5, 0xa5, 0xa5, 0xa5]))
