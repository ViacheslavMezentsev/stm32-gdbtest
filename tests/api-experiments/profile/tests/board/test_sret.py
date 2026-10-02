"""Pinned ARM base-PCS return-buffer experiment; not a general adapter."""
import struct
import gdb
from stm32_gdbtest import case
from lab.session import Research


@case('HW_R5_STRUCT_SRET', labels=('research', 'abi'))
def sret(t):
    t.check('reviewed soft-float ELF', t.report['elf_sha256'],
            'db27a41c0115eb83d0a7a808b6f68d59098ec20be91f98b1a9a48ae10e6abe0e')
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set debug remote on')
    address = int(gdb.parse_and_eval('(unsigned int)transform_pair')) & ~1
    with Research(t, (0x20000000, 0x20000)) as r:
        r.run_until('*' + hex(address))
        frame = gdb.newest_frame()
        t.check('exact entry before prologue', int(frame.pc()), address)
        t.check('reviewed caller', frame.older().name(), 'process_returns')
        destination = int(frame.read_register('r0'))
        sp = int(frame.read_register('sp'))
        t.check('reviewed caller return slot', destination, sp)
        t.check('return object size', int(gdb.lookup_type('struct ReturnPair').sizeof), 8)
        t.check('aligned slot within consumer SRAM',
                destination % 8 == 0 and 0x20000004 <= destination <= 0x20020000 - 12, True)
        inferior = gdb.selected_inferior()
        before = bytes(inferior.read_memory(destination - 4, 16))
        payload = struct.pack('<iI', -7, 19)
        r.record('mutation_intent', {'destination': destination, 'size': 8,
                                    'before': list(before[4:12]), 'payload': list(payload)})
        inferior.write_memory(destination, payload)
        after = bytes(inferior.read_memory(destination - 4, 16))
        t.check('slot and surrounding bytes', after.hex(), (before[:4] + payload + before[12:]).hex())
        gdb.execute('return')
        t.check('caller selected after bare return', gdb.newest_frame().name(), 'process_returns')
        r.run_until('process_returns')
        value = gdb.parse_and_eval('accepted_pair')
        actual = {name: int(value[name]) for name in ('code', 'count')}
        r.record('caller_value', actual)
        t.check('caller consumed replacement buffer', actual, {'code': -7, 'count': 19})
        r.run_until('process_returns')
        value = gdb.parse_and_eval('accepted_pair')
        t.check('following natural struct', {name: int(value[name]) for name in ('code', 'count')},
                {'code': -8, 'count': 20})
