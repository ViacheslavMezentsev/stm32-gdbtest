from stm32_gdbtest import case


@case("HW_CI_BOOT", labels=("boot",), contracts=("ci_app_api",))
def boot(target):
    # Target.boot has already reached main, before board_init.
    target.check("initialized interval", target.value("app_delay"), 500)
    target.check("BSS loop count", target.value("app_state.ticks"), 0)
    target.check("BSS LED state", target.value("app_state.led"), 0)
    target.check("BSS milliseconds", target.value("board_ticks_ms"), 0)
    target.reach("app_loop")
    before = target.value("app_state.ticks")
    target.reach("app_loop")
    target.check("app_state.ticks advanced", target.value("app_state.ticks") - before, 1)


@case("HW_CI_GPIO", labels=("gpio",), contracts=("ci_gpio_macros",))
def gpio(target):
    # CMSIS macros are visible in board.c, the translation unit that includes the device header.
    target.reach("board_led_toggle")
    target.check("PA5 clock", target.value("(RCC->AHBENR & RCC_AHBENR_GPIOAEN) != 0"), 1)
    target.check("PA5 output", target.value("(GPIOA->MODER & GPIO_MODER_MODER5) == GPIO_MODER_MODER5_0"), 1)
    target.check("push-pull", target.value("GPIOA->OTYPER & GPIO_OTYPER_OT_5"), 0)
    target.check("low speed", target.value("GPIOA->OSPEEDR & GPIO_OSPEEDR_OSPEEDR5"), 0)
    target.check("no pull", target.value("GPIOA->PUPDR & GPIO_PUPDR_PUPDR5"), 0)
    target.check("initial LED off", target.value("GPIOA->ODR & GPIO_ODR_5"), 0)


@case("HW_CI_CLOCK", labels=("clock",), contracts=("ci_clock_macros",))
def clock(target):
    target.reach("board_led_toggle")
    target.check("HSI enabled and ready", target.value("(RCC->CR & (RCC_CR_HSION | RCC_CR_HSIRDY)) == (RCC_CR_HSION | RCC_CR_HSIRDY)"), 1)
    target.check("SYSCLK HSI, AHB/APB divide by one", target.value("RCC->CFGR & (RCC_CFGR_SW | RCC_CFGR_SWS | RCC_CFGR_HPRE | RCC_CFGR_PPRE)"), 0)
    target.check("nominal core frequency", target.value("SystemCoreClock"), 8000000)
    target.check("1 ms reload at nominal 8 MHz", target.value("SysTick->LOAD"), 7999)
    # Reading CTRL clears COUNTFLAG; the application uses the IRQ counter, not that flag.
    target.check("SysTick enabled, interrupt, core clock", target.value("SysTick->CTRL & (SysTick_CTRL_ENABLE_Msk | SysTick_CTRL_TICKINT_Msk | SysTick_CTRL_CLKSOURCE_Msk)"), 7)


@case("HW_CI_BLINK", labels=("gpio", "timing"), contracts=("ci_gpio_macros",))
def blink(target):
    target.reach("board_led_toggle")
    target.check("initial Low", target.value("(GPIOA->ODR & GPIO_ODR_5) != 0"), 0)
    before = target.value("board_ticks_ms")
    for level in (1, 0):
        target.reach("board_led_toggle")
        now = target.value("board_ticks_ms")
        target.check("alternating PA5", target.value("(GPIOA->ODR & GPIO_ODR_5) != 0"), level)
        target.check("at least 500 firmware milliseconds", ((now - before) & 0xFFFFFFFF) >= 500, True)
        before = now
