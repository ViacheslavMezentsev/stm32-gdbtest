"""
RU: Проверки запуска, GPIO, тактирования и периферии платы.
EN: Board startup, GPIO, clock and peripheral checks.
"""
from stm32_gdbtest import case

# Application interval of the CI firmware.
# Application interval of the fixture profile (`[app] delay_ms` in api.toml).
EXPECTED_DELAY = 500


# Verify initialized state and progress into the application loop.
@case("HW_CI_BOOT", labels=("boot",), contracts=("ci_app_api",))
def boot(target):
    # Target.boot has already reached main, before board_init.
    target.check_table([
        ('initialized interval', 'app_delay', EXPECTED_DELAY),
        ('BSS loop count', 'app_state.ticks', 0),
        ('BSS LED state', 'app_state.led', 0),
        ('BSS milliseconds', 'board_ticks_ms', 0)
    ])

    target.reach("app_loop")
    before = target.read("app_state.ticks")
    target.reach("app_loop")

    # Check that execution advances through the application loop.
    target.check("app_state.ticks advanced", target.read("app_state.ticks") - before, 1)


# Verify the board LED pin configuration and initial output state.
@case("HW_CI_GPIO", labels=("gpio",), contracts=("ci_gpio_macros",))
def gpio(target):
    # CMSIS macros are visible in board.c, the translation unit that includes the device header.
    target.reach("board_led_toggle")

    # Check register and application state against the expected values.
    target.check_table([
        ('PG13 clock', '(RCC->AHB1ENR & RCC_AHB1ENR_GPIOGEN) != 0', 1),
        ('PG13 output', 'GPIOG->MODER & GPIO_MODER_MODER13', 1 << 26),
        ('push-pull', 'GPIOG->OTYPER & GPIO_OTYPER_OT13', 0),
        ('low speed', 'GPIOG->OSPEEDR & GPIO_OSPEEDER_OSPEEDR13', 0),
        ('no pull', 'GPIOG->PUPDR & GPIO_PUPDR_PUPD13', 0),
        ('initial LED off (Low)', 'GPIOG->ODR & GPIO_ODR_OD13', 0)
    ])


# Verify clock selection, bus dividers and the system tick configuration.
@case("HW_CI_CLOCK", labels=("clock",), contracts=("ci_clock_macros",))
def clock(target):
    # TECH-001: docs/ru/TESTING_TECHNIQUES.md#tech-001 (EN: docs/en/TESTING_TECHNIQUES.md#tech-001).
    target.reach("board_led_toggle")

    # Check the clock source, bus dividers and nominal SysTick period.
    target.check(
        "HSI enabled and ready",
        target.read("(RCC->CR & (RCC_CR_HSION | RCC_CR_HSIRDY)) == (RCC_CR_HSION | RCC_CR_HSIRDY)"),
        1
    )
    target.check(
        "SYSCLK HSI, AHB/APB divide by one",
        target.read("RCC->CFGR & (RCC_CFGR_SW | RCC_CFGR_SWS | RCC_CFGR_HPRE | RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2)"),
        0
    )
    target.check("nominal core frequency", target.read("SystemCoreClock"), 16000000)
    target.check("1 ms reload at nominal 16 MHz", target.read("SysTick->LOAD"), 15999)

    # Reading CTRL clears COUNTFLAG; the application uses the IRQ counter, not that flag.
    target.check(
        "SysTick enabled, interrupt, core clock",
        target.read(
            "SysTick->CTRL & (SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_CLKSOURCE_Msk)"
        ),
        7
    )


# Observe consecutive LED transitions and their firmware timing.
@case("HW_CI_BLINK", labels=("gpio", "timing"), contracts=("ci_gpio_macros",))
def blink(target):
    target.reach("board_led_toggle")

    # Verify initial Low.
    target.check("initial Low", target.read("(GPIOG->ODR & GPIO_ODR_OD13) != 0"), 0)

    before = target.read("board_ticks_ms")

    # Observe alternating output levels and check the elapsed firmware ticks.
    for level in (1, 0):
        target.reach("board_led_toggle")
        now = target.read("board_ticks_ms")

        # Check alternating output levels and the minimum firmware interval.
        target.check("alternating PG13", target.read("(GPIOG->ODR & GPIO_ODR_OD13) != 0"), level)
        target.check("at least the configured interval", ((now - before) & 0xFFFFFFFF)
                 >= EXPECTED_DELAY, True)

        before = now


# Verify timer clock, counter configuration and interrupt routing.
@case("HW_CI_TIM2_INIT", labels=("timer", "init"), contracts=("ci_timer_macros",))
def timer_init(target):
    target.reach("board_led_toggle")

    # Check register and application state against the expected values.
    target.check_table([
        ('TIM2 clock', '(RCC->APB1ENR & RCC_APB1ENR_TIM2EN) != 0', 1),
        ('TIM2 prescaler', 'TIM2->PSC', 15999),
        ('TIM2 period', 'TIM2->ARR', 99),
        ('TIM2 internal clock', 'TIM2->SMCR', 0),
        ('TIM2 upcounter enabled', 'TIM2->CR1', 1),
        ('update interrupt only', 'TIM2->DIER', 1),
        ('NVIC TIM2 enabled', '(NVIC->ISER[0] >> 28) & 1', 1),
        ('TIM2 vector', '(unsigned int)vectors[44] & ~1U', '(unsigned int)TIM2_IRQHandler & ~1U')
    ])


# Observe timer interrupt handling and advancement of the event counter.
@case("HW_CI_TIM2_IRQ", labels=("timer", "irq"), contracts=("ci_timer_macros",))
def timer_irq(target):
    # Run to actual exception entries, without EGR/NVIC/software injection.
    target.reach("TIM2_IRQHandler")

    # Observe consecutive timer interrupts and the event counter between them.
    for _ in range(2):
        # Check the active timer exception and pending update flag.
        target.check("TIM2 exception number", target.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 44)
        target.check("update pending", target.read("TIM2->SR & TIM_SR_UIF"), 1)

        before = target.read("board_timer_events")
        target.reach("TIM2_IRQHandler")

        # Verify one event published.
        target.check("one event published", target.read("board_timer_events"), (before + 1) & 0xFFFFFFFF)

    # A permanently asserted update IRQ would starve thread mode.
    target.reach("board_delay_ms")

    # Verify thread mode resumes.
    target.check("thread mode resumes", target.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 0)


# Observe a natural SysTick interrupt and verify tick publication.
@case("HW_CI_SYSTICK_IRQ", labels=("clock", "irq"), contracts=("ci_clock_macros",))
def systick_irq(target):
    # TECH-001/002: observe CMSIS state in board.c; natural IRQ, no pending injection.
    target.reach("SysTick_Handler")

    # Check interrupt routing and the active SysTick exception.
    target.check(
        "SysTick vector",
        target.read("(unsigned int)vectors[15] & ~1U"),
        target.read("(unsigned int)SysTick_Handler & ~1U")
    )
    target.check("SysTick exception", target.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 15)

    before = target.read("board_ticks_ms")
    target.reach("SysTick_Handler")

    # Verify one millisecond published.
    target.check("one millisecond published", target.read("board_ticks_ms"), (before + 1) & 0xFFFFFFFF)

    target.reach("board_delay_ms")

    # Verify thread resumes.
    target.check("thread resumes", target.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 0)
