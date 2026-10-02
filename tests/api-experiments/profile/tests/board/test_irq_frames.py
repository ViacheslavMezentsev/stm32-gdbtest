"""R11 runs against the existing CMSIS F411 firmware, not api_firmware.elf."""
import gdb
from stm32_gdbtest import case
from lab.session import Research


def number(frame, register):
    return int(frame.read_register(register)) & 0xffffffff


def exercise(t, handler, exception, counter):
    gdb.execute('monitor gdb_breakpoint_override hard')
    gdb.execute('monitor debug_level 3')
    gdb.execute('set breakpoint auto-hw on')
    gdb.execute('set displaced-stepping off')
    gdb.execute('set debug remote on')
    value = gdb.lookup_global_symbol('board_ticks_ms').value()
    with Research(t, (int(value.address), 4)) as r:
        # Initialization also calls this function with 2 ms; select the application delay.
        t.reach('board_delay_ms', when='delay_ms == 500')
        address = int(gdb.parse_and_eval('(unsigned int)' + handler)) & ~1
        interrupted = None
        for attempt in range(8):
            r.run_until('*' + hex(address))
            frame = gdb.newest_frame()
            t.check('handler PC at exact entry', int(frame.pc()), address)
            t.check('handler active exception', number(frame, 'xPSR') & 0x1ff, exception)
            older = frame.older()
            skipped = 0
            while older is not None and older.type() == gdb.SIGTRAMP_FRAME and skipped < 4:
                skipped += 1
                older = older.older()
            r.record('candidate_' + str(attempt), dict(frames=r.frames(), skipped=skipped))
            if older is None:
                raise RuntimeError('No interrupted frame')
            if older.name() == 'board_delay_ms':
                interrupted = older
                break
        if interrupted is None:
            raise RuntimeError('No board_delay_ms interruption within eight attempts')

        handler_frame = gdb.newest_frame()
        exc_return = number(handler_frame, 'lr')
        # This experiment only decodes basic thread/MSP exception frames, without FPU stacking.
        t.check('basic thread MSP EXC_RETURN', exc_return, 0xfffffff9)
        sp = number(handler_frame, 'sp')
        t.check('stack frame lies within F411 SRAM', 0x20000000 <= sp <= 0x20020000 - 32, True)
        data = bytes(gdb.selected_inferior().read_memory(sp, 32))
        names = ('r0', 'r1', 'r2', 'r3', 'r12', 'lr', 'pc', 'xPSR')
        stacked = {name: int.from_bytes(data[i * 4:i * 4 + 4], 'little') for i, name in enumerate(names)}
        resume_sp = sp + 32 + (4 if stacked['xPSR'] & (1 << 9) else 0)
        t.check('stacked context is thread mode', stacked['xPSR'] & 0x1ff, 0)
        t.check('unwound PC equals hardware stack', int(interrupted.pc()), stacked['pc'])
        t.check('unwound SP includes alignment', number(interrupted, 'sp'), resume_sp)
        original_selection = gdb.selected_frame()
        try:
            interrupted.select()
            delay = int(gdb.parse_and_eval('delay_ms'))
            start_value = interrupted.read_var('start')
            start = ({'state': 'optimized_out'} if start_value.is_optimized_out else
                     {'state': 'available', 'value': int(start_value)})
            t.check('interrupted local argument', delay, 500)
        finally:
            original_selection.select()
        t.check('selected handler restored', gdb.selected_frame() == original_selection, True)
        before = int(gdb.parse_and_eval(counter))
        r.record('exception', dict(handler=handler, exc_return=exc_return, sp=sp,
                                  stacked=stacked, resume_sp=resume_sp, delay=delay, start=start,
                                  counter_before=before, frames=r.frames()))
        # A real code address from the exception frame; LR is an EXC_RETURN token, not code.
        r.run_until('*' + hex(stacked['pc']))
        resumed = gdb.newest_frame()
        t.check('returned to thread mode', number(resumed, 'xPSR') & 0x1ff, 0)
        t.check('returned to original function', resumed.name(), 'board_delay_ms')
        t.check('resumed SP', number(resumed, 'sp'), resume_sp)
        actual = {name: number(resumed, name) for name in names if name != 'xPSR'}
        expected = {name: stacked[name] for name in actual}
        t.check('hardware restored volatile registers and PC', actual, expected)
        after = int(gdb.parse_and_eval(counter))
        t.check('handler performed its work', (after - before) & 0xffffffff > 0, True)
        r.record('returned', dict(registers=actual, counter_after=after, frames=r.frames()))
        r.run_until('app_loop')
        t.check('application progresses after IRQ', int(gdb.parse_and_eval('app_state.ticks')) > 0, True)


@case('HW_R11_SYSTICK', labels=('research', 'irq'))
def systick(t):
    exercise(t, 'SysTick_Handler', 15, 'board_ticks_ms')


@case('HW_R11_TIM2', labels=('research', 'irq'))
def timer(t):
    exercise(t, 'TIM2_IRQHandler', 44, 'board_timer_events')
