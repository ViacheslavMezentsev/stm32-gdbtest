"""E3: retain original F411 SysTick sleep checks, replace raw frame traversal."""

from dataclasses import asdict
import gdb
from stm32_gdbtest import case
from stack_context import GdbContexts, interrupted_frame, caller_is
from board_config import settings


@case('HW_E3_CONTEXT', contracts=('ci_sleep_macros',))
def context(t):
    evidence = []
    with GdbContexts() as contexts:
        t.reach('board_delay_ms', when='delay_ms == 500')
        t.check('ordinary Sleep, no SLEEPONEXIT', t.value('SCB->SCR & 6'), 0)
        enabled = t.value('NVIC->ISER[0]')
        enabled1 = t.value('NVIC->ISER[1]') if settings(t)['nvic_banks'] > 1 else None
        if enabled1 is not None:
            t.set_value('NVIC->ICER[1]', enabled1)
        t.set_value('NVIC->ICER[0]', enabled)
        contexts.invalidate()  # explicit notification for interventions outside facade
        before = t.value('board_ticks_ms')
        matched = None
        try:
            for attempt in range(8):
                t.reach('SysTick_Handler')
                t.check('expected exception', t.value('SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk'), 15)
                captured = contexts.capture()
                frame = interrupted_frame(captured.stack)
                instruction = t.value(f'*(unsigned short*)({frame.pc} - 2)')
                evidence.append({'attempt':attempt, 'context':asdict(captured),
                                 'preceding_halfword':instruction})
                if frame.function == 'board_delay_ms' and instruction == 0xBF30:
                    t.check('interrupted instruction is WFI', instruction, 0xBF30)
                    matched = captured
                    t.check('caller at explicit depth',
                            caller_is(captured.stack, 'board_delay_ms', depth=frame.index), True)
                    t.check('PC is handler PC', captured['PC'], t.value('$pc'))
                    t.check('SP is handler SP', captured['SP'], t.value('$sp'))
                    # Verify selection independence without exposing frame handles to snapshot users.
                    selected = gdb.selected_frame()
                    try:
                        gdb.newest_frame().older().select()
                        again = contexts.capture()
                        t.check('PC independent of selected frame', again['PC'], captured['PC'])
                        t.check('SP independent of selected frame', again['SP'], captured['SP'])
                    finally:
                        selected.select()
                    limited = contexts.capture(max_frames=1)
                    t.check('depth limit explicit', limited.stack.termination, 'depth_limit')
                    t.check('truncated caller unknown', caller_is(limited.stack, 'board_delay_ms'), None)
                    break
            t.check('WFI interrupted context observed', matched is not None, True)
        finally:
            t.set_value('NVIC->ISER[0]', enabled)
            if enabled1 is not None:
                t.set_value('NVIC->ISER[1]', enabled1)
            contexts.invalidate()
        t.check('mutation invalidates context', contexts.current(matched), False)
        fresh = contexts.capture()
        t.reach('app_loop')
        t.check('resume invalidates context', contexts.current(fresh), False)
        t.check('history still readable', matched['PC'], evidence[-1]['context']['PC'])
        t.check('delay completed', ((t.value('board_ticks_ms') - before) & 0xFFFFFFFF) >= 500, True)
        t.check('ADC sequence retained', t.value('board_adc_sequences'), 1)
    t.report['e3_evidence'] = {'observations':evidence, 'event_handlers_after_close':len(contexts.handlers)}
    t.check('event handlers released', len(contexts.handlers), 0)
