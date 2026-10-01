"""F401 WFI interrupted context, not a power or sleep-residency measurement."""
import gdb
from stm32_gdbtest import case


def reach_wfi_irq(target, handler, exception):
    # TECH-008: docs/ru/TESTING_TECHNIQUES.md#tech-008 (EN: docs/en/TESTING_TECHNIQUES.md#tech-008).
    # An IRQ can arrive before WFI: bound retries and inspect the interrupted frame.
    for attempt in range(8):
        target.reach(handler)
        target.check("expected exception", target.value("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), exception)
        interrupted = gdb.newest_frame().older()
        # GDB may insert an exception/signal trampoline between the two frames.
        for _ in range(4):
            if interrupted is None or interrupted.type() != gdb.SIGTRAMP_FRAME:
                break
            interrupted = interrupted.older()
        if interrupted is None:
            raise RuntimeError("GDB cannot unwind the interrupted Cortex-M frame")
        pc = int(interrupted.pc())
        name = interrupted.name()
        instruction = target.value(f"*(unsigned short*)({pc} - 2)")
        target.report.setdefault("interrupted_contexts", []).append(
            dict(attempt=attempt, function=name, pc=pc, preceding_halfword=instruction))
        if name == "board_delay_ms" and instruction == 0xBF30:
            target.check("interrupted instruction is WFI", instruction, 0xBF30)
            return
    target.check("WFI interrupted context observed", False, True)


@case("HW_CI_SLEEP_SYSTICK", labels=("sleep", "systick"), contracts=("ci_sleep_macros",))
def sleep_systick(target):
    target.reach("board_delay_ms", when="delay_ms == 500")
    target.check("ordinary Sleep, no SLEEPONEXIT", target.value("SCB->SCR & 6"), 0)
    enabled = target.value("NVIC->ISER[0]")
    enabled1 = target.value("NVIC->ISER[1]")
    target.set_value("NVIC->ICER[1]", enabled1)
    target.set_value("NVIC->ICER[0]", enabled)
    before = target.value("board_ticks_ms")
    try:
        reach_wfi_irq(target, "SysTick_Handler", 15)
    finally:
        target.set_value("NVIC->ISER[0]", enabled)
        target.set_value("NVIC->ISER[1]", enabled1)
    target.reach("app_loop")
    target.check("delay completed", ((target.value("board_ticks_ms") - before) & 0xFFFFFFFF) >= 500, True)
    target.check("ADC sequence retained", target.value("board_adc_sequences"), 1)


@case("HW_CI_SLEEP_TIM2", labels=("sleep", "timer"), contracts=("ci_sleep_macros",))
def sleep_tim2(target):
    target.reach("board_delay_ms", when="delay_ms == 500")
    target.check("ordinary Sleep, no SLEEPONEXIT", target.value("SCB->SCR & 6"), 0)
    control = target.value("SysTick->CTRL") & 7
    enabled = target.value("NVIC->ISER[0]")
    enabled1 = target.value("NVIC->ISER[1]")
    target.set_value("NVIC->ICER[1]", enabled1)
    # Leave only TIM2 external IRQ, stop SysTick and clear a pending exception.
    target.set_value("NVIC->ICER[0]", enabled & ~(1 << 28))
    target.set_value("SysTick->CTRL", 0)
    target.set_value("SCB->ICSR", 1 << 25)
    ticks = target.value("board_ticks_ms")
    events = target.value("board_timer_events")
    try:
        reach_wfi_irq(target, "TIM2_IRQHandler", 44)
        target.check("SysTick did not advance", target.value("board_ticks_ms"), ticks)
    finally:
        target.set_value("SysTick->CTRL", control)
        target.set_value("NVIC->ISER[0]", enabled)
        target.set_value("NVIC->ISER[1]", enabled1)
    target.reach("app_loop")
    target.check("timer event handled", ((target.value("board_timer_events") - events) & 0xFFFFFFFF) > 0, True)
    target.check("ADC sequence retained", target.value("board_adc_sequences"), 1)
