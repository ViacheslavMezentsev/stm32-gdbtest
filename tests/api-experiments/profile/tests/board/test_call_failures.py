"""R10 expected ERRORs: CPU bus fault and a non-returning inferior call."""
import json
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


def word(address):
    return int.from_bytes(gdb.selected_inferior().read_memory(address, 4), 'little')


@case('HW_R10_FAULT', labels=('research', 'calls', 'negative'))
def fault(t):
    with setup(t) as r:
        r.run_until('process_sample')
        guard = next(bp for bp in t.owned if bp.is_valid() and bp.location == 'HardFault_Handler')
        r.record('attempt', {'expression': 'sum_bytes((uint8_t *)0x20020000, 1, 0)',
                             'invalid_read': 0x20020000, 'cfsr_before': word(0xe000ed28)})
        try:
            # First byte beyond this F411's 128 KiB SRAM; CPU read only, no MMIO writes.
            gdb.parse_and_eval('sum_bytes((uint8_t *)0x20020000, 1, 0)')
        except gdb.error:
            frames = r.frames()
            evidence = dict(event=r.last_stop, frames=frames,
                            guard_hit=guard.number in (r.last_stop or {}).get('breakpoints', []),
                            exception=int(gdb.newest_frame().read_register('xPSR')) & 0x1ff,
                            dummy_count=sum(f['type'] == gdb.DUMMY_FRAME for f in frames),
                            cfsr=word(0xe000ed28), hfsr=word(0xe000ed2c), bfar=word(0xe000ed38))
            r.record('fault', evidence)
            t.check('HardFault guard identified', evidence['guard_hit'], True)
            t.check('HardFault exception active', evidence['exception'], 3)
            t.check('precise read fault with valid BFAR', evidence['cfsr'] & 0x8200, 0x8200)
            t.check('fault escalated', bool(evidence['hfsr'] & 0x40000000), True)
            t.check('faulting data address', evidence['bfar'], 0x20020000)
            t.check('dummy frame retained through exception', evidence['dummy_count'], 1)
            raise
        raise RuntimeError('Invalid read unexpectedly returned')


@case('HW_R10_TIMEOUT', timeout_s=8, labels=('research', 'calls', 'negative'))
def timeout(t):
    with setup(t) as r:
        r.run_until('process_sample')
        request = json.loads(Path(os.environ['STM32_GDBTEST_RUN']).read_text(encoding='utf-8'))
        marker = Path(request['result']).with_name('entered-call.json')

        bp = r.breakpoint('Default_Handler')
        number = bp.number
        failure = None
        try:
            gdb.parse_and_eval('Default_Handler()')
        except gdb.error as exc:
            failure = str(exc)
        t.check('loop entry breakpoint', number in (r.last_stop or {}).get('breakpoints', []), True)
        t.check('call interrupted at entry', failure is not None, True)
        frame = gdb.newest_frame()
        pc = int(frame.pc())
        frames = r.frames()
        evidence = dict(function=frame.name(), pc=pc, frames=frames, call_error=failure,
                        dummy_count=sum(f['type'] == gdb.DUMMY_FRAME for f in frames),
                        exception=int(frame.read_register('xPSR')) & 0x1ff,
                        instruction_hex=bytes(gdb.selected_inferior().read_memory(pc, 2)).hex(),
                        gdb=gdb.VERSION)
        t.check('one dummy before continuation', evidence['dummy_count'], 1)
        t.check('entry is Thumb self-loop', evidence['instruction_hex'], 'fee7')
        bp.delete()
        # Persist the proven call entry before external timeout kills the GDB process.
        marker.write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
        gdb.execute('continue')
        raise RuntimeError('Non-returning call unexpectedly completed')


@case('HW_R10_CONTROL', labels=('research', 'calls'))
def control(t):
    with setup(t) as r:
        r.run_until('process_sample')
        t.check('thread mode after previous failure', int(gdb.newest_frame().read_register('xPSR')) & 0x1ff, 0)
        t.check('reset cleared fault status', word(0xe000ed28), 0)
        t.check('fresh inferior call', int(gdb.parse_and_eval('sum_bytes(sample.bytes, 8, 5)')), 775)
        r.run_until('process_sample')
        t.check('natural checksum after recovery', int(gdb.parse_and_eval('checksum')), 773 ^ 0xffffff85)
