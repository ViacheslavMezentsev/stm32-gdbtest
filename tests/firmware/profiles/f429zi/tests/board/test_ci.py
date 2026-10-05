"""
RU: Проверки запуска, GPIO, тактирования и периферии платы.
EN: Board startup, GPIO, clock and peripheral checks.
"""
from stm32_gdbtest import case

# HSI is the system clock of the fixture (RM: 16 MHz nominal).
HSI_HZ = 16_000_000
# TIM2 counts at 1 kHz and overflows every 100 ms.
TIMER_TICK_HZ = 1_000
TIMER_PERIOD_TICKS = 100

# Firmware counters are uint32_t and wrap around.
U32_MASK = 0xFFFFFFFF

# Application interval of the CI firmware.
# Application interval of the fixture profile (`[app] delay_ms` in api.toml).
EXPECTED_DELAY = 500


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
    # CMSIS macros are visible in board.c, the translation unit that includes the device header.
    t.reach("board_led_toggle")

    # Check register and application state against the expected values.
    t.check([
        ('PG13 clock', 'RCC->AHB1ENR & RCC_AHB1ENR_GPIOGEN'),
        ('PG13 output', 'GPIOG->MODER & GPIO_MODER_MODER13', 'GPIO_MODER_MODER13_0'),
        ('push-pull', 'GPIOG->OTYPER & GPIO_OTYPER_OT13', 0),
        ('low speed', 'GPIOG->OSPEEDR & GPIO_OSPEEDER_OSPEEDR13', 0),
        ('no pull', 'GPIOG->PUPDR & GPIO_PUPDR_PUPD13', 0),
        ('initial LED off (Low)', 'GPIOG->ODR & GPIO_ODR_OD13', 0)
    ])


# Verify clock selection, bus dividers and the system tick configuration.
@case("HW_CI_CLOCK", labels=("clock",), contracts=("ci_clock_macros",))
def clock(t):
    # TECH-001: docs/ru/TESTING_TECHNIQUES.md#tech-001 (EN: docs/en/TESTING_TECHNIQUES.md#tech-001).
    t.reach("board_led_toggle")

    # Check the clock source, bus dividers and nominal SysTick period.
    t.check(
        "HSI enabled and ready",
        t.read("(RCC->CR & (RCC_CR_HSION | RCC_CR_HSIRDY)) == (RCC_CR_HSION | RCC_CR_HSIRDY)"),
        1
    )
    t.check(
        "SYSCLK HSI, AHB/APB divide by one",
        t.read("RCC->CFGR & (RCC_CFGR_SW | RCC_CFGR_SWS | RCC_CFGR_HPRE | RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2)"),
        0
    )
    t.check("nominal core frequency", t.read("SystemCoreClock"), HSI_HZ)
    t.check("1 ms reload at nominal 16 MHz", t.read("SysTick->LOAD"), HSI_HZ // 1000 - 1)

    # Reading CTRL clears COUNTFLAG; the application uses the IRQ counter, not that flag.
    t.check(
        "SysTick enabled, interrupt, core clock",
        t.read(
            "SysTick->CTRL & (SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_CLKSOURCE_Msk)"
        ),
        7
    )


# Observe consecutive LED transitions and their firmware timing.
@case("HW_CI_BLINK", labels=("gpio", "timing"), contracts=("ci_gpio_macros",))
def blink(t):
    t.reach("board_led_toggle")

    # Verify initial Low.
    t.check("initial Low", t.read("(GPIOG->ODR & GPIO_ODR_OD13) != 0"), 0)

    before = t.read("board_ticks_ms")

    # Observe alternating output levels and check the elapsed firmware ticks.
    for level in (1, 0):
        t.reach("board_led_toggle")
        now = t.read("board_ticks_ms")

        # Check alternating output levels and the minimum firmware interval.
        t.check("alternating PG13", t.read("(GPIOG->ODR & GPIO_ODR_OD13) != 0"), level)
        t.check("at least the configured interval", ((now - before) & U32_MASK)
                 >= EXPECTED_DELAY)

        before = now


# Verify timer clock, counter configuration and interrupt routing.
@case("HW_CI_TIM2_INIT", labels=("timer", "init"), contracts=("ci_timer_macros",))
def timer_init(t):
    t.reach("board_led_toggle")

    # Check register and application state against the expected values.
    t.check([
        ('TIM2 clock', 'RCC->APB1ENR & RCC_APB1ENR_TIM2EN'),
        ('TIM2 prescaler', 'TIM2->PSC', HSI_HZ // TIMER_TICK_HZ - 1),
        ('TIM2 period', 'TIM2->ARR', TIMER_PERIOD_TICKS - 1),
        ('TIM2 internal clock', 'TIM2->SMCR', 0),
        ('TIM2 upcounter enabled', 'TIM2->CR1', 'TIM_CR1_CEN'),
        ('update interrupt only', 'TIM2->DIER', 'TIM_DIER_UIE'),
        ('NVIC TIM2 enabled', 'NVIC->ISER[TIM2_IRQn >> 5] & (1UL << (TIM2_IRQn & 31))'),
        ('TIM2 vector', '(unsigned int)vectors[TIM2_IRQn + 16] & ~1U', '(unsigned int)TIM2_IRQHandler & ~1U')
    ])


# Observe timer interrupt handling and advancement of the event counter.
@case("HW_CI_TIM2_IRQ", labels=("timer", "irq"), contracts=("ci_timer_macros",))
def timer_irq(t):
    # Run to actual exception entries, without EGR/NVIC/software injection.
    t.reach("TIM2_IRQHandler")

    # Observe consecutive timer interrupts and the event counter between them.
    for _ in range(2):
        # Check the active timer exception and pending update flag.
        t.check("TIM2 exception number", t.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), t.evaluate("TIM2_IRQn + 16"))
        t.check("update pending", t.read("TIM2->SR & TIM_SR_UIF"), t.evaluate("TIM_SR_UIF"))

        before = t.read("board_timer_events")
        t.reach("TIM2_IRQHandler")

        # Verify one event published.
        t.check("one event published", t.read("board_timer_events"), (before + 1) & U32_MASK)

    # A permanently asserted update IRQ would starve thread mode.
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
