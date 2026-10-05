"""
RU: Проверки контекста WFI и пробуждения по прерыванию; не измерение энергопотребления.
EN: WFI interrupted context and IRQ wake-up checks; not a power measurement.
"""
import gdb
from stm32_gdbtest import case

# Thumb encoding of WFI (ARMv6-M/ARMv7-M ARM).
WFI_OPCODE = 0xBF30

# Firmware counters are uint32_t and wrap around.
U32_MASK = 0xFFFFFFFF

# Application interval of the CI firmware.
# Application interval of the fixture profile (`[app] delay_ms` in api.toml).
EXPECTED_DELAY = 500


# Find an interrupt that actually interrupted WFI, using bounded frame inspection.
def reach_wfi_irq(t, handler, exception):
    # TECH-008: docs/ru/TESTING_TECHNIQUES.md#tech-008 (EN: docs/en/TESTING_TECHNIQUES.md#tech-008).
    # An IRQ can arrive before WFI: bound retries and inspect the interrupted frame.
    for attempt in range(8):
        t.reach(handler)

        # Check the active exception before inspecting the interrupted frame.
        t.check("expected exception", t.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), t.evaluate(exception))

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
        instruction = t.read(f"*(unsigned short*)({pc} - 2)")
        t.report.setdefault("interrupted_contexts", []).append(
            dict(attempt=attempt, function=name, pc=pc, preceding_halfword=instruction))
        if name == "board_delay_ms" and instruction == WFI_OPCODE:
            # Verify interrupted instruction is WFI.
            t.check("interrupted instruction is WFI", instruction, WFI_OPCODE)

            return

    # Fail explicitly when bounded retries never observe an interrupted WFI.
    t.check("WFI interrupted context observed", False, True)


# Verify ordinary Sleep and application progress after a SysTick interrupt.
@case("HW_CI_SLEEP_SYSTICK", timeout_s=90, labels=("sleep", "systick"), contracts=("ci_sleep_macros",))
def sleep_systick(t):
    # Stop in the delay call whose requested interval is the agreed application delay.
    t.reach("board_delay_ms")
    t.check("the delay runs for the application interval",
                 t.read("app_delay") == EXPECTED_DELAY)

    # Verify ordinary Sleep, no SLEEPONEXIT.
    t.check("ordinary Sleep, no SLEEPONEXIT", t.read("SCB->SCR & (SCB_SCR_SLEEPONEXIT_Msk | SCB_SCR_SLEEPDEEP_Msk)"), 0)

    enabled = t.read("NVIC->ISER[0]")
    t.write("NVIC->ICER[0]", enabled)
    before = t.read("board_ticks_ms")
    try:
        reach_wfi_irq(t, "SysTick_Handler", "SysTick_IRQn + 16")
    finally:
        t.write("NVIC->ISER[0]", enabled)

    # The first stop in the loop can be inside the interval itself, so a full loop entry is awaited.
    t.reach("app_loop")
    t.reach("app_loop")

    # Check application progress and retained ADC publication after wake-up.
    t.check("delay completed",
                 ((t.read("board_ticks_ms") - before) & U32_MASK) >= EXPECTED_DELAY)
    t.check("ADC sequence retained", t.read("board_adc_sequences"), 1)


# Isolate TIM3 as the wake source and verify interrupted WFI and recovery.
@case("HW_CI_SLEEP_TIM3", timeout_s=90, labels=("sleep", "timer"), contracts=("ci_sleep_macros",))
def sleep_tim3(t):
    # Stop in the delay call whose requested interval is the agreed application delay.
    t.reach("board_delay_ms")
    t.check("the delay runs for the application interval",
                 t.read("app_delay") == EXPECTED_DELAY)

    # Verify ordinary Sleep, no SLEEPONEXIT.
    t.check("ordinary Sleep, no SLEEPONEXIT", t.read("SCB->SCR & (SCB_SCR_SLEEPONEXIT_Msk | SCB_SCR_SLEEPDEEP_Msk)"), 0)

    control = t.read("SysTick->CTRL") & 7
    enabled = t.read("NVIC->ISER[0]")

    # Leave only TIM3 external IRQ, stop SysTick and clear a pending exception.
    t.write("NVIC->ICER[0]", enabled & ~(1 << t.evaluate("TIM3_IRQn")))
    t.write("SysTick->CTRL", 0)
    t.write("SCB->ICSR", "SCB_ICSR_PENDSTCLR_Msk")
    ticks = t.read("board_ticks_ms")
    events = t.read("board_timer_events")
    try:
        reach_wfi_irq(t, "TIM3_IRQHandler", "TIM3_IRQn + 16")

        # Verify SysTick did not advance.
        t.check("SysTick did not advance", t.read("board_ticks_ms"), ticks)
    finally:
        t.write("SysTick->CTRL", control)
        t.write("NVIC->ISER[0]", enabled)

    # A full loop entry follows a completed interval and its ADC publication.
    t.reach("app_loop")
    t.reach("app_loop")

    # Verify timer event handled.
    t.check("timer event handled", ((t.read("board_timer_events") - events) & U32_MASK) > 0)
    t.check("ADC sequence retained", t.read("board_adc_sequences"), 1)
