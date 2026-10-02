"""R12: DMA buffer changes versus CPU hardware watchpoint observations; CMSIS ELF."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


def watch(r, expression, access):
    bp = gdb.Breakpoint(expression, type=gdb.BP_WATCHPOINT, wp_class=access)
    r.owned.append(bp)
    return bp


def stopped(r):
    r.last_stop = None
    gdb.execute('continue')
    return dict(r.last_stop or {})


def exercise(t, access):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set debug remote on')
    value = gdb.lookup_global_symbol('board_adc_buffer').value()
    with Research(t, (int(value.address), int(value.type.sizeof))) as r:
        r.run_until('board_adc_sample')
        t.check('first transfer not completed yet', t.value('board_adc_sequences'), 0)
        before = r.read_memory(*r.ram)
        bp = watch(r, 'board_adc_buffer', access)
        t.check('hardware watch type', bp.type,
                gdb.BP_HARDWARE_WATCHPOINT if access == gdb.WP_WRITE else gdb.BP_ACCESS_WATCHPOINT)
        irq_address = t.value('(unsigned int)DMA2_Stream0_IRQHandler') & ~1
        sentinel = r.breakpoint('*' + hex(irq_address))
        event = stopped(r)
        after = r.read_memory(*r.ram)
        completion = dict(event=event, before=before.hex(), after=after.hex(),
                          watch_number=bp.number, sentinel_number=sentinel.number,
                          pc=int(gdb.newest_frame().pc()), ndtr=t.value('DMA2_Stream0->NDTR'),
                          status=t.value('DMA2->LISR'), stream=t.value('DMA2_Stream0->CR'),
                          sequences=t.value('board_adc_sequences'))
        r.record('dma_completion', completion)
        t.check('completion sentinel reached', sentinel.number in event.get('breakpoints', []), True)
        t.check('no reported buffer watch at DMA completion', bp.number in event.get('breakpoints', []), False)
        t.check('exact entry before CPU buffer reads', completion['pc'], irq_address)
        t.check('DMA IRQ active', t.value('$xPSR') & 0x1ff, 72)
        t.check('DMA changed RAM', after != before, True)
        t.check('two halfwords transferred', completion['ndtr'], 0)
        t.check('transfer complete flag', bool(completion['status'] & (1 << 5)), True)
        t.check('normal-mode stream disabled', completion['stream'] & 1, 0)
        t.check('handler has not incremented sequence', completion['sequences'], 0)
        samples = [int.from_bytes(after[i:i + 2], 'little') for i in (0, 2)]
        t.check('ADC samples in 12-bit range', all(0 < v <= 4095 for v in samples), True)
        sentinel.delete()

        if access == gdb.WP_ACCESS:
            event = stopped(r)
            r.record('cpu_access_control', dict(event=event, function=gdb.newest_frame().name(),
                                              pc=int(gdb.newest_frame().pc())))
            t.check('same watch catches CPU buffer access', bp.number in event.get('breakpoints', []), True)
            t.check('CPU reader is DMA handler', gdb.newest_frame().name(), 'DMA2_Stream0_IRQHandler')
            bp.delete()
        else:
            bp.delete()
            control = watch(r, 'board_adc_sequences', gdb.WP_WRITE)
            t.check('CPU control uses hardware write watch', control.type, gdb.BP_HARDWARE_WATCHPOINT)
            event = stopped(r)
            r.record('cpu_write_control', dict(event=event, sequence=t.value('board_adc_sequences')))
            t.check('CPU write watch identity', control.number in event.get('breakpoints', []), True)
            t.check('CPU completed one sequence', t.value('board_adc_sequences'), 1)
            control.delete()
        r.run_until('board_delay_ms')
        t.check('caller reached normal delay', t.value('delay_ms'), 500)
        t.check('consumer copied temperature', t.value('board_temperature_raw'), samples[0])
        t.check('consumer copied reference', t.value('board_reference_raw'), samples[1])
        t.check('exactly one completed sequence', t.value('board_adc_sequences'), 1)
        t.check('no application ADC error', t.value('board_adc_error'), 0)
        r.record('consumed', dict(samples=samples, sequences=t.value('board_adc_sequences')))


@case('HW_R12_WRITE', labels=('research', 'dma', 'watch'))
def dma_write(t):
    exercise(t, gdb.WP_WRITE)


@case('HW_R12_ACCESS', labels=('research', 'dma', 'watch'))
def dma_access(t):
    exercise(t, gdb.WP_ACCESS)
