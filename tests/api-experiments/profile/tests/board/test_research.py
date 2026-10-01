from stm32_gdbtest import case
import gdb
from lab.session import Research


def lab(target):
    value = gdb.lookup_global_symbol('sample').value()
    return Research(target, (int(value.address), int(value.type.sizeof)))


def rejected(target, label, action, error=ValueError):
    try:
        action()
    except error:
        target.check(label, True, True)
    else:
        target.check(label, False, True)


@case('HW_R1_VALUES', labels=('research',))
def values(t):
    with lab(t) as r:
        data = r.read('sample')
        fields = data['value']
        for key, expected in [('signed_value', -123), ('wide_value', 0x123456789abcdef0),
                              ('gain', 3.5), ('mode', 3)]:
            t.check(key, fields[key]['value'], expected)
        t.check('bytes', [v['value'] for v in fields['bytes']['value']], [0, 1, 2, 3, 127, 128, 254, 255])
        t.check('bounded string', bytes(v['value'] for v in fields['name']['value']).hex(), b'sensor\0\0'.hex())
        r.record('sample', data)
        rejected(t, 'reject call expression', lambda: r.read('process_sample()'))
        rejected(t, 'reject assignment', lambda: r.read('cycles=1'))
        rejected(t, 'reject invalid index', lambda: r.read('sample.bytes[8]'))
        rejected(t, 'missing symbol', lambda: r.read('missing_sample'))


@case('HW_R1_FRAMES', labels=('research',))
def frames(t):
    with lab(t) as r:
        r.run_until('sum_bytes')
        handle = r.frame()
        t.check('count argument', r.local(handle, 'count')['value'], 8)
        t.check('seed argument', r.local(handle, 'seed')['value'], 3)
        rows = r.frames()
        t.check('nested frames', [v['name'] for v in rows[:3]], ['sum_bytes', 'process_sample', 'main'])
        r.record('frames', rows)
        r.run_until('process_sample')
        rejected(t, 'stale frame rejected', lambda: r.local(handle, 'count'))
        t.check('snapshot survives resume', rows[0]['name'], 'sum_bytes')


@case('HW_R1_RAM', labels=('research',))
def ram(t):
    with lab(t) as r:
        r.run_until('process_sample')
        start, size = r.ram
        before = r.read_memory(start, size)
        address = int(gdb.lookup_global_symbol('sample').value()['bytes'].address)
        for width in (1, 2, 4, 8):
            data = bytes(range(32, 32 + width))
            with r.patch_ram(address, data):
                t.check('RAM payload ' + str(width), r.read_memory(address, width).hex(), data.hex())
                current = r.read_memory(start, size)
                offset = address - start
                t.check('outside patch unchanged', (current[:offset] + current[offset + width:]).hex(),
                        (before[:offset] + before[offset + width:]).hex())
            t.check('restored ' + str(width), r.read_memory(start, size).hex(), before.hex())
        rejected(t, 'range checked before write', lambda: r.read_memory(start - 1, 1))
        try:
            with r.patch_ram(address, b'xyz'):
                raise ValueError('body failure')
        except ValueError:
            pass
        t.check('exception rollback', r.read_memory(start, size).hex(), before.hex())


@case('HW_R1_STOPS', labels=('research',))
def stops(t):
    guards = [bp.number for bp in t.owned if bp.is_valid()]
    with lab(t) as r:
        first = r.run_until('process_sample')
        second = r.run_until('*' + hex(first['pc']))
        t.check('address stop', second['pc'], first['pc'])
        line = gdb.find_pc_line(first['pc'])
        third = r.run_until(line.symtab.filename + ':' + str(line.line))
        t.check('source stop reason', third['reason'], 'expected')
        external = t.breakpoint('sum_bytes')
        try:
            r.run_until('sum_bytes')
            t.check('external point survives', external.is_valid(), True)
            # Four guards + external + this point exhaust the six-location budget.
            r.breakpoint('process_sample')
            rejected(t, 'location budget checked', lambda: r.breakpoint('main'))
        finally:
            r.clear()
            external.delete()
        rejected(t, 'missing location', lambda: r.breakpoint('missing_function'))
    t.check('guards survive scope', [bp.number for bp in t.owned if bp.is_valid()], guards)


@case('HW_R1_RECORD', labels=('research',))
def record(t):
    with lab(t) as r:
        source = {'value': [1, 2]}
        r.record('snapshot', source)
        source['value'][0] = 99
        t.check('evidence is materialized', r.evidence['snapshot']['value'], [1, 2])
        rejected(t, 'duplicate evidence', lambda: r.record('snapshot', {}))
        rejected(t, 'oversize evidence', lambda: r.record('large', 'x' * 20000))
        rejected(t, 'NaN rejected', lambda: r.record('nan', float('nan')))
        rejected(t, 'live object rejected', lambda: r.record('object', object()), TypeError)
        r.record('status', 'namespace cannot overwrite root status')
        t.check('root status protected', t.report['status'], 'ERROR')


@case('HW_R1_CONTROL', labels=('research', 'boot'))
def control(t):
    with lab(t) as r:
        r.run_until('process_sample')
        t.check('first sequence', r.local(r.frame(), 'sequence')['value'], 0)
        r.run_until('process_sample')
        t.check('natural checksum', r.read('checksum')['value'], (770 + 3) ^ (0xffffffff - 122))
        t.check('completed cycle', r.read('cycles')['value'], 1)
