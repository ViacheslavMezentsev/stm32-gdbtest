"""R7 exact unaligned range decomposition using available hardware points."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


@case('HW_R7_SPLIT', labels=('research', 'watch'))
def split(t):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set debug remote on')
    sample = gdb.lookup_global_symbol('sample').value()
    with Research(t, (int(sample.address), int(sample.type.sizeof))) as r:
        base = int(gdb.parse_and_eval('&sample.bytes[0]'))
        t.check('reviewed misalignment', base % 4, 1)
        for size, parts in ((2, ((0, 1), (1, 1))), (4, ((0, 1), (1, 2), (3, 1)))):
            t.boot(t.profile['reset_halt'])
            r.run_until('sum_bytes')
            covered = [offset + byte for offset, width in parts for byte in range(width)]
            t.check('exact coverage without outside bytes', covered, list(range(size)))
            points = []
            for offset, width in parts:
                address = base + offset
                t.check('part alignment', address % width, 0)
                t.check('part within known object', r.ram[0] <= address and address + width <= sum(r.ram), True)
                bp = gdb.Breakpoint('*(uint8_t (*)[%d])%s' % (width, hex(address)),
                                    type=gdb.BP_WATCHPOINT, wp_class=gdb.WP_READ)
                t.check('part hardware', bp.type, gdb.BP_READ_WATCHPOINT)
                points.append(bp)
                r.owned.append(bp)
            sentinel = r.breakpoint('process_packet')
            hits = []
            for _ in range(size + 1):
                r.last_stop = None
                gdb.execute('continue')
                stop = dict(r.last_stop or {})
                numbers = stop.get('breakpoints', [])
                if sentinel.number in numbers:
                    break
                t.check('watch access in intended function', gdb.newest_frame().name(), 'sum_bytes')
                owners = [index for index, bp in enumerate(points) if bp.number in numbers]
                t.check('one known part hit', len(owners), 1)
                hits.append(owners[0])
            r.record('split_' + str(size), {'parts': [list(p) for p in parts], 'hits': hits,
                                          'sentinel': sentinel.number in numbers})
            t.check('all byte loads and no outside hits', hits, [0, 1] if size == 2 else [0, 1, 1, 2])
            t.check('left watched function', sentinel.number in numbers, True)
            for bp in points:
                bp.delete()
            sentinel.delete()
