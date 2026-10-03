from stm32_gdbtest import case




def _check_values(target, rows):
    # TECH-010: evaluate each actual, then its expected expression, then check.
    for name, expression, expected in rows:
        actual = target.value(expression)
        if isinstance(expected, str):
            expected = target.value(expected)
        target.check(name, actual, expected)


@case("HW_CI_BOOT", labels=("boot",), contracts=("ci_app_api",))
def boot(target):
    # Target.boot has already reached main, before board_init.
    _check_values(target, [
        ('initialized interval', 'app_delay', 500),
        ('BSS loop count', 'app_state.ticks', 0),
        ('BSS LED state', 'app_state.led', 0),
        ('BSS milliseconds', 'board_ticks_ms', 0),
    ])
    target.reach("app_loop")
    before = target.value("app_state.ticks")
    target.reach("app_loop")
    target.check("app_state.ticks advanced", target.value("app_state.ticks") - before, 1)


@case("HW_CI_GPIO", labels=("gpio",), contracts=("ci_gpio_macros",))
def gpio(target):
    # CMSIS macros are visible in board.c, the translation unit that includes the device header.
    target.reach("board_led_toggle")
    _check_values(target, [
        ('PC13 clock', '(RCC->AHB1ENR & RCC_AHB1ENR_GPIOCEN) != 0', 1),
        ('PC13 output', 'GPIOC->MODER & GPIO_MODER_MODER13', 1 << 26),
        ('push-pull', 'GPIOC->OTYPER & GPIO_OTYPER_OT13', 0),
        ('low speed', 'GPIOC->OSPEEDR & GPIO_OSPEEDER_OSPEEDR13', 0),
        ('no pull', 'GPIOC->PUPDR & GPIO_PUPDR_PUPD13', 0),
        ('initial LED off (High)', 'GPIOC->ODR & GPIO_ODR_OD13', 1 << 13),
    ])


@case("HW_CI_CLOCK", labels=("clock",), contracts=("ci_clock_macros",))
def clock(target):
    # TECH-001: docs/ru/TESTING_TECHNIQUES.md#tech-001 (EN: docs/en/TESTING_TECHNIQUES.md#tech-001).
    target.reach("board_led_toggle")
    target.check("HSI enabled and ready", target.value("(RCC->CR & (RCC_CR_HSION | RCC_CR_HSIRDY)) == (RCC_CR_HSION | RCC_CR_HSIRDY)"), 1)
    target.check("SYSCLK HSI, AHB/APB divide by one", target.value("RCC->CFGR & (RCC_CFGR_SW | RCC_CFGR_SWS | RCC_CFGR_HPRE | RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2)"), 0)
    target.check("nominal core frequency", target.value("SystemCoreClock"), 16000000)
    target.check("1 ms reload at nominal 16 MHz", target.value("SysTick->LOAD"), 15999)
    # Reading CTRL clears COUNTFLAG; the application uses the IRQ counter, not that flag.
    target.check("SysTick enabled, interrupt, core clock", target.value("SysTick->CTRL & (SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_CLKSOURCE_Msk)"), 7)


@case("HW_CI_BLINK", labels=("gpio", "timing"), contracts=("ci_gpio_macros",))
def blink(target):
    target.reach("board_led_toggle")
    target.check("initial High", target.value("(GPIOC->ODR & GPIO_ODR_OD13) != 0"), 1)
    before = target.value("board_ticks_ms")
    for level in (0, 1):
        target.reach("board_led_toggle")
        now = target.value("board_ticks_ms")
        target.check("alternating PC13", target.value("(GPIOC->ODR & GPIO_ODR_OD13) != 0"), level)
        target.check("at least 500 firmware milliseconds", ((now - before) & 0xFFFFFFFF) >= 500, True)
        before = now


@case("HW_CI_TIM2_INIT", labels=("timer", "init"), contracts=("ci_timer_macros",))
def timer_init(target):
    target.reach("board_led_toggle")
    _check_values(target, [
        ('TIM2 clock', '(RCC->APB1ENR & RCC_APB1ENR_TIM2EN) != 0', 1),
        ('TIM2 prescaler', 'TIM2->PSC', 15999),
        ('TIM2 period', 'TIM2->ARR', 99),
        ('TIM2 internal clock', 'TIM2->SMCR', 0),
        ('TIM2 upcounter enabled', 'TIM2->CR1', 1),
        ('update interrupt only', 'TIM2->DIER', 1),
        ('NVIC TIM2 enabled', '(NVIC->ISER[0] >> 28) & 1', 1),
        ('TIM2 vector', '(unsigned int)vectors[44] & ~1U', '(unsigned int)TIM2_IRQHandler & ~1U'),
    ])


@case("HW_CI_TIM2_IRQ", labels=("timer", "irq"), contracts=("ci_timer_macros",))
def timer_irq(target):
    # Run to actual exception entries, without EGR/NVIC/software injection.
    target.reach("TIM2_IRQHandler")
    for _ in range(2):
        target.check("TIM2 exception number", target.value("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 44)
        target.check("update pending", target.value("TIM2->SR & TIM_SR_UIF"), 1)
        before = target.value("board_timer_events")
        target.reach("TIM2_IRQHandler")
        target.check("one event published", target.value("board_timer_events"), (before + 1) & 0xFFFFFFFF)
    # A permanently asserted update IRQ would starve thread mode.
    target.reach("board_delay_ms")
    target.check("thread mode resumes", target.value("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 0)


@case("HW_CI_SYSTICK_IRQ", labels=("clock", "irq"), contracts=("ci_clock_macros",))
def systick_irq(target):
    # TECH-001/002: observe CMSIS state in board.c; natural IRQ, no pending injection.
    target.reach("SysTick_Handler")
    target.check("SysTick vector", target.value("(unsigned int)vectors[15] & ~1U"), target.value("(unsigned int)SysTick_Handler & ~1U"))
    target.check("SysTick exception", target.value("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 15)
    before = target.value("board_ticks_ms")
    target.reach("SysTick_Handler")
    target.check("one millisecond published", target.value("board_ticks_ms"), (before + 1) & 0xFFFFFFFF)
    target.reach("board_delay_ms")
    target.check("thread resumes", target.value("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 0)
