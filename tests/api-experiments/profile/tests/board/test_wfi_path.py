"""R13: bounded WFI/IRQ/return paths on the existing CMSIS F411 ELF."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


def exercise(t, timer):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set displaced-stepping off')
    gdb.execute('set debug remote on')
    ticks = gdb.lookup_global_symbol('board_ticks_ms').value()
    with Research(t, (int(ticks.address), 4)) as r:
        t.reach('board_delay_ms', when='delay_ms == 500')
        t.check('ordinary sleep without SLEEPONEXIT', t.value('SCB->SCR & 6'), 0)
        block = gdb.block_for_pc(int(gdb.newest_frame().pc()))
        while block.function is None:
            block = block.superblock
        instructions = gdb.newest_frame().architecture().disassemble(block.start, block.end)
        points = [i for i in instructions if i['asm'].strip() == 'wfi']
        t.check('one WFI in selected function', len(points), 1)
        wfi = points[0]['addr']
        t.check('Thumb WFI encoding', bytes(gdb.selected_inferior().read_memory(wfi, 2)).hex(), '30bf')
        enabled = [t.value('NVIC->ISER[%d]' % i) for i in range(2)]
        control = t.value('SysTick->CTRL') & 7
        handler = 'TIM2_IRQHandler' if timer else 'SysTick_Handler'
        exception = 44 if timer else 15
        counter = 'board_timer_events' if timer else 'board_ticks_ms'
        tick_before = t.value('board_ticks_ms')
        before = t.value(counter)
        try:
            t.set_value('NVIC->ICER[1]', enabled[1])
            t.set_value('NVIC->ICER[0]', enabled[0] & ~(1 << 28) if timer else enabled[0])
            if timer:
                t.set_value('SysTick->CTRL', 0)
                t.set_value('SCB->ICSR', 1 << 25)
            r.run_until('*' + hex(wfi))
            r.record('before_wfi', dict(pc=int(gdb.newest_frame().pc()), instruction=points[0],
                                       ticks=t.value('board_ticks_ms'), timer=timer,
                                       enabled=enabled, systick_control=control))
            handler_address = t.value('(unsigned int)' + handler) & ~1
            resume_pc = None
            resume_sp = None
            for attempt in range(8):
                r.run_until('*' + hex(handler_address))
                t.check('expected wake exception', t.value('$xPSR') & 0x1ff, exception)
                older = gdb.newest_frame().older()
                for _ in range(4):
                    if older is None or older.type() != gdb.SIGTRAMP_FRAME:
                        break
                    older = older.older()
                if older is None:
                    raise RuntimeError('Cannot unwind interrupted WFI context')
                pc = int(older.pc())
                r.record('wake_' + str(attempt), dict(pc=pc, function=older.name(), frames=r.frames()))
                if older.name() == 'board_delay_ms' and pc == wfi + 2:
                    resume_pc = pc
                    resume_sp = int(older.read_register('sp')) & 0xffffffff
                    break
            t.check('post-WFI interrupted context observed', resume_pc, wfi + 2)
            r.run_until('*' + hex(resume_pc))
            t.check('resumed thread mode', t.value('$xPSR') & 0x1ff, 0)
            t.check('resumed stack', int(gdb.newest_frame().read_register('sp')) & 0xffffffff, resume_sp)
            t.check('wake handler performed work', ((t.value(counter) - before) & 0xffffffff) > 0, True)
            if timer:
                t.check('TIM2 wake does not advance SysTick timebase', t.value('board_ticks_ms'), tick_before)
            r.record('after_wake', dict(pc=int(gdb.newest_frame().pc()), counter=t.value(counter),
                                       ticks=t.value('board_ticks_ms')))
        finally:
            if timer:
                t.set_value('SysTick->CTRL', control)
            for i in range(2):
                t.set_value('NVIC->ISER[%d]' % i, enabled[i])
            t.check('IRQ enable masks restored', [t.value('NVIC->ISER[%d]' % i) for i in range(2)], enabled)
            t.check('SysTick control bits restored', t.value('SysTick->CTRL') & 7, control)
        r.run_until('app_loop')
        t.check('full delay eventually completed', ((t.value('board_ticks_ms') - tick_before) & 0xffffffff) >= 500, True)
        t.check('one ADC sequence retained', t.value('board_adc_sequences'), 1)


@case('HW_R13_SYSTICK', labels=('research', 'sleep'))
def systick(t):
    exercise(t, False)


@case('HW_R13_TIM2', labels=('research', 'sleep'))
def timer(t):
    exercise(t, True)
