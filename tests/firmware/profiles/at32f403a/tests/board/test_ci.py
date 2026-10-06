"""
RU: Проверки запуска, GPIO, тактирования и таймера платы AT32F403A (битовые поля CMSIS Artery).
EN: AT32F403A board startup, GPIO, clock and timer checks (Artery CMSIS bit fields).
"""
from stm32_gdbtest import case


# HICK is the system clock of the fixture (RM: 8 MHz nominal).
HICK_HZ = 8_000_000
# TMR2 counts at 1 kHz and overflows every 100 ms.
TIMER_TICK_HZ = 1_000
TIMER_PERIOD_TICKS = 100

# Firmware counters are uint32_t and wrap around.
U32_MASK = 0xFFFFFFFF

# Application interval of the fixture profile (`[app] delay_ms` in api.toml).
EXPECTED_DELAY = 500

# GPIO mode of PC13 (RM GPIO configuration): output with moderate drive (IOMC = 10), push-pull (IOFC = 00).
IOMC_OUTPUT_MODERATE = 2
IOFC_PUSH_PULL = 0


# Verify initialized state and progress into the application loop.
@case("HW_CI_BOOT", labels=("boot",), contracts=("ci_app_api",))
def boot(t):
    # Target.boot has already reached main, before board_init.
    t.check([
        ('initialized interval', 'app_delay', EXPECTED_DELAY),
        ('BSS loop count', 'app_state.ticks', 0),
        ('BSS LED state', 'app_state.led', 0),
        ('BSS milliseconds', 'board_ticks_ms', 0)
    ])

    t.reach("app_loop")
    before = t.read("app_state.ticks")
    t.reach("app_loop")

    # Check that execution advances through the application loop.
    t.check("app_state.ticks advanced", t.read("app_state.ticks") - before, 1)


# Verify the board LED pin configuration and initial output state.
@case("HW_CI_GPIO", labels=("gpio",), contracts=("ci_gpio_macros",))
def gpio(t):
    # The peripheral macros are visible in board.c, the translation unit that includes the device header.
    t.reach("board_led_toggle")

    # Check the clock, the pin mode and the initial level (high: LED off on an active-low board).
    t.check([
        ('PC13 clock', 'CRM->apb2en_bit.gpiocen', 1),
        ('PC13 output, moderate drive', 'GPIOC->cfghr_bit.iomc13', IOMC_OUTPUT_MODERATE),
        ('PC13 push-pull', 'GPIOC->cfghr_bit.iofc13', IOFC_PUSH_PULL),
        ('initial LED off (high)', 'GPIOC->odt_bit.odt13', 1)
    ])


# Verify clock selection, bus dividers and the system tick configuration.
@case("HW_CI_CLOCK", labels=("clock",), contracts=("ci_clock_macros",))
def clock(t):
    # TECH-001: docs/ru/TESTING_TECHNIQUES.md#tech-001 (EN: docs/en/TESTING_TECHNIQUES.md#tech-001).
    t.reach("board_led_toggle")

    # Reading SysTick->CTRL clears COUNTFLAG; the application uses the IRQ counter, not that flag.
    systick_running = "SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_CLKSOURCE_Msk"

    # Check the clock source, bus dividers and nominal SysTick period.
    t.check([
        ("HICK enabled", "CRM->ctrl_bit.hicken", 1),
        ("HICK stable", "CRM->ctrl_bit.hickstbl", 1),
        ("SCLK HICK selected and active", "CRM->cfg_bit.sclksel | CRM->cfg_bit.sclksts", 0),
        ("AHB/APB divide by one", "CRM->cfg_bit.ahbdiv | CRM->cfg_bit.apb1div | CRM->cfg_bit.apb2div", 0),
        ("nominal core frequency", "SystemCoreClock", HICK_HZ),
        ("1 ms reload at nominal 8 MHz", "SysTick->LOAD", HICK_HZ // 1000 - 1),
        ("SysTick enabled, interrupt, core clock", f"SysTick->CTRL & ({systick_running})", systick_running)
    ])


# Observe consecutive LED transitions and their firmware timing.
@case("HW_CI_BLINK", labels=("gpio", "timing"), contracts=("ci_gpio_macros",))
def blink(t):
    t.reach("board_led_toggle")

    # Verify the initial high level (LED off).
    t.check("initial High", t.read("GPIOC->odt_bit.odt13"), 1)

    before = t.read("board_ticks_ms")

    # Observe alternating output levels and check the elapsed firmware ticks.
    for level in (0, 1):
        t.reach("board_led_toggle")
        now = t.read("board_ticks_ms")

        # Check alternating output levels and the minimum firmware interval.
        t.check("alternating PC13", t.read("GPIOC->odt_bit.odt13"), level)
        t.check("at least the configured interval", ((now - before) & U32_MASK) >= EXPECTED_DELAY)

        before = now


# Verify timer clock, counter configuration and interrupt routing.
@case("HW_CI_TIM2_INIT", labels=("timer", "init"), contracts=("ci_timer_macros",))
def timer_init(t):
    t.reach("board_led_toggle")

    # Check register and application state against the expected values.
    t.check([
        ('TMR2 clock', 'CRM->apb1en_bit.tmr2en', 1),
        ('TMR2 divider', 'TMR2->div', HICK_HZ // TIMER_TICK_HZ - 1),
        ('TMR2 period', 'TMR2->pr', TIMER_PERIOD_TICKS - 1),
        ('TMR2 internal clock', 'TMR2->stctrl', 0),
        ('TMR2 upcounter enabled', 'TMR2->ctrl1', 'TMR2->ctrl1_bit.tmren'),
        ('TMR2 counter enabled', 'TMR2->ctrl1_bit.tmren', 1),
        ('overflow interrupt only', 'TMR2->iden', 'TMR2->iden_bit.ovfien'),
        ('NVIC TMR2 enabled', 'NVIC->ISER[TMR2_GLOBAL_IRQn >> 5] & (1UL << (TMR2_GLOBAL_IRQn & 31))'),
        ('TMR2 vector', '(unsigned int)vectors[TMR2_GLOBAL_IRQn + 16] & ~1U', '(unsigned int)TIM2_IRQHandler & ~1U')
    ])


# Observe timer interrupt handling and advancement of the event counter.
@case("HW_CI_TIM2_IRQ", labels=("timer", "irq"), contracts=("ci_timer_macros",))
def timer_irq(t):
    # Run to actual exception entries, without software event or NVIC injection.
    t.reach("TIM2_IRQHandler")

    # Observe consecutive timer interrupts and the event counter between them.
    for _ in range(2):
        # Check the active timer exception and the pending overflow flag.
        t.check("TMR2 exception number", t.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"),
                t.evaluate("TMR2_GLOBAL_IRQn + 16"))
        t.check("overflow pending", t.read("TMR2->ists_bit.ovfif"), 1)

        before = t.read("board_timer_events")
        t.reach("TIM2_IRQHandler")

        # Verify one event published.
        t.check("one event published", t.read("board_timer_events"), (before + 1) & U32_MASK)

    # A permanently asserted overflow IRQ would starve thread mode.
    t.reach("board_delay_ms")

    # Verify thread mode resumes.
    t.check("thread mode resumes", t.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 0)


# Observe a natural SysTick interrupt and verify tick publication.
@case("HW_CI_SYSTICK_IRQ", labels=("clock", "irq"), contracts=("ci_clock_macros",))
def systick_irq(t):
    # TECH-001/002: observe CMSIS state in board.c; natural IRQ, no pending injection.
    t.reach("SysTick_Handler")

    # Check interrupt routing and the active SysTick exception.
    t.check(
        "SysTick vector",
        t.read("(unsigned int)vectors[SysTick_IRQn + 16] & ~1U"),
        t.read("(unsigned int)SysTick_Handler & ~1U")
    )
    t.check("SysTick exception", t.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), t.evaluate("SysTick_IRQn + 16"))

    before = t.read("board_ticks_ms")
    t.reach("SysTick_Handler")

    # Verify one millisecond published.
    t.check("one millisecond published", t.read("board_ticks_ms"), (before + 1) & U32_MASK)

    t.reach("board_delay_ms")

    # Verify thread resumes.
    t.check("thread resumes", t.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 0)
