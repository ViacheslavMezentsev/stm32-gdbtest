"""
RU: Проверки контекста WFI и пробуждения по прерыванию; не измерение энергопотребления.
EN: WFI interrupted context and IRQ wake-up checks; not a power measurement.
"""
import gdb
from stm32_gdbtest import case

# Application interval of the CI firmware.
# Application interval of the fixture profile (`[app] delay_ms` in api.toml).
EXPECTED_DELAY = 500


# Find an interrupt that actually interrupted WFI, using bounded frame inspection.
def reach_wfi_irq(target, handler, exception):
    # TECH-008: docs/ru/TESTING_TECHNIQUES.md#tech-008 (EN: docs/en/TESTING_TECHNIQUES.md#tech-008).
    # An IRQ can arrive before WFI: bound retries and inspect the interrupted frame.
    for attempt in range(8):
        target.reach(handler)

        # Check the active exception before inspecting the interrupted frame.
        target.check("expected exception", target.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), exception)

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
        instruction = target.read(f"*(unsigned short*)({pc} - 2)")
        target.report.setdefault("interrupted_contexts", []).append(
            dict(attempt=attempt, function=name, pc=pc, preceding_halfword=instruction))
        if name == "board_delay_ms" and instruction == 0xBF30:
            # Verify interrupted instruction is WFI.
            target.check("interrupted instruction is WFI", instruction, 0xBF30)

            return

    # Fail explicitly when bounded retries never observe an interrupted WFI.
    target.check("WFI interrupted context observed", False, True)


# Verify ordinary Sleep and application progress after a SysTick interrupt.
@case("HW_CI_SLEEP_SYSTICK", timeout_s=90, labels=("sleep", "systick"), contracts=("ci_sleep_macros",))
def sleep_systick(target):
    # Stop in the delay call whose requested interval is the agreed application delay.
    target.reach("board_delay_ms")
    target.check("the delay runs for the application interval",
                 target.read("app_delay") == EXPECTED_DELAY, True)

    # Verify ordinary Sleep, no SLEEPONEXIT.
    target.check("ordinary Sleep, no SLEEPONEXIT", target.read("SCB->SCR & 6"), 0)

    enabled = target.read("NVIC->ISER[0]")
    enabled1 = target.read("NVIC->ISER[1]")
    target.write("NVIC->ICER[1]", enabled1)
    target.write("NVIC->ICER[0]", enabled)
    before = target.read("board_ticks_ms")
    try:
        reach_wfi_irq(target, "SysTick_Handler", 15)
    finally:
        target.write("NVIC->ISER[0]", enabled)
        target.write("NVIC->ISER[1]", enabled1)

    # The first stop in the loop can be inside the interval itself, so a full loop entry is awaited.
    target.reach("app_loop")
    target.reach("app_loop")

    # Check application progress and retained ADC publication after wake-up.
    target.check("delay completed",
                 ((target.read("board_ticks_ms") - before) & 0xFFFFFFFF) >= EXPECTED_DELAY, True)
    target.check("ADC sequence retained", target.read("board_adc_sequences"), 1)


# Isolate TIM2 as the wake source and verify interrupted WFI and recovery.
@case("HW_CI_SLEEP_TIM2", timeout_s=90, labels=("sleep", "timer"), contracts=("ci_sleep_macros",))
def sleep_tim2(target):
    # Stop in the delay call whose requested interval is the agreed application delay.
    target.reach("board_delay_ms")
    target.check("the delay runs for the application interval",
                 target.read("app_delay") == EXPECTED_DELAY, True)

    # Verify ordinary Sleep, no SLEEPONEXIT.
    target.check("ordinary Sleep, no SLEEPONEXIT", target.read("SCB->SCR & 6"), 0)

    control = target.read("SysTick->CTRL") & 7
    enabled = target.read("NVIC->ISER[0]")
    enabled1 = target.read("NVIC->ISER[1]")
    target.write("NVIC->ICER[1]", enabled1)

    # Leave only TIM2 external IRQ, stop SysTick and clear a pending exception.
    target.write("NVIC->ICER[0]", enabled & ~(1 << 28))
    target.write("SysTick->CTRL", 0)
    target.write("SCB->ICSR", 1 << 25)
    ticks = target.read("board_ticks_ms")
    events = target.read("board_timer_events")
    try:
        reach_wfi_irq(target, "TIM2_IRQHandler", 44)

        # Verify SysTick did not advance.
        target.check("SysTick did not advance", target.read("board_ticks_ms"), ticks)
    finally:
        target.write("SysTick->CTRL", control)
        target.write("NVIC->ISER[0]", enabled)
        target.write("NVIC->ISER[1]", enabled1)

    # A full loop entry follows a completed interval and its ADC publication.
    target.reach("app_loop")
    target.reach("app_loop")

    # Verify timer event handled.
    target.check("timer event handled", ((target.read("board_timer_events") - events) & 0xFFFFFFFF) > 0, True)
    target.check("ADC sequence retained", target.read("board_adc_sequences"), 1)
