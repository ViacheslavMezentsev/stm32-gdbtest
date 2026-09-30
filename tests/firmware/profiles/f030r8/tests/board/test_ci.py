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


@case("HW_CI_TIM3_INIT", labels=("timer", "init"), contracts=("ci_timer_macros",))
def timer_init(target):
    target.reach("board_led_toggle")
    target.check("TIM3 clock", target.value("(RCC->APB1ENR & RCC_APB1ENR_TIM3EN) != 0"), 1)
    target.check("TIM3 prescaler", target.value("TIM3->PSC"), 7999)
    target.check("TIM3 period", target.value("TIM3->ARR"), 99)
    target.check("TIM3 internal clock", target.value("TIM3->SMCR"), 0)
    target.check("TIM3 upcounter enabled", target.value("TIM3->CR1"), 1)
    target.check("update interrupt only", target.value("TIM3->DIER"), 1)
    target.check("NVIC TIM3 enabled", target.value("(NVIC->ISER[0] >> 16) & 1"), 1)
    target.check("TIM3 vector", target.value("(unsigned int)vectors[32] & ~1U"), target.value("(unsigned int)TIM3_IRQHandler & ~1U"))


@case("HW_CI_TIM3_IRQ", labels=("timer", "irq"), contracts=("ci_timer_macros",))
def timer_irq(target):
    # Run to actual exception entries, without EGR/NVIC/software injection.
    target.reach("TIM3_IRQHandler")
    for _ in range(2):
        target.check("TIM3 exception number", target.value("$xPSR & 0x1ff"), 32)
        target.check("update pending", target.value("TIM3->SR & TIM_SR_UIF"), 1)
        before = target.value("board_timer_events")
        target.reach("TIM3_IRQHandler")
        target.check("one event published", target.value("board_timer_events"), (before + 1) & 0xFFFFFFFF)
    # A permanently asserted update IRQ would starve thread mode on this M0.
    target.reach("board_delay_ms")
    target.check("thread mode resumes", target.value("$xPSR & 0x1ff"), 0)


@case("HW_CI_ADC_INIT", labels=("adc", "dma", "init"), contracts=("ci_adc_macros",))
def adc_init(target):
    target.reach("board_adc_sample")
    target.check("HSI14 ready", target.value("(RCC->CR2 & RCC_CR2_HSI14RDY) != 0"), 1)
    target.check("ADC clock", target.value("(RCC->APB2ENR & RCC_APB2ENR_ADC1EN) != 0"), 1)
    target.check("DMA clock", target.value("(RCC->AHBENR & RCC_AHBENR_DMA1EN) != 0"), 1)
    target.check("async ADC clock", target.value("ADC1->CFGR2 & ADC_CFGR2_CKMODE"), 0)
    target.check("forward single 12bit scan", target.value("ADC1->CFGR1"), 0)
    target.check("channels16/17", target.value("ADC1->CHSELR"), (1 << 16) | (1 << 17))
    target.check("239.5 sample cycles", target.value("ADC1->SMPR"), 7)
    target.check("internal paths", target.value("ADC1_COMMON->CCR & (ADC_CCR_TSEN | ADC_CCR_VREFEN)"), (1 << 23) | (1 << 22))
    target.check("calibration finished, ADC enabled", target.value("ADC1->CR & (ADC_CR_ADCAL | ADC_CR_ADEN)"), 1)
    target.check("DMA normal halfwords, increment, TC/TE IRQ", target.value("DMA1_Channel1->CCR"), 0x58A)
    target.check("DMA peripheral address", target.value("DMA1_Channel1->CPAR"), target.value("&ADC1->DR"))
    target.check("DMA SRAM buffer", target.value("DMA1_Channel1->CMAR"), target.value("&board_adc_buffer[0]"))
    target.check("DMA NVIC enabled", target.value("(NVIC->ISER[0] >> 9) & 1"), 1)
    target.check("DMA vector", target.value("(unsigned int)vectors[25] & ~1U"), target.value("(unsigned int)DMA1_Channel1_IRQHandler & ~1U"))
    target.check("no init error", target.value("board_adc_error"), 0)


@case("HW_CI_ADC_DMA", labels=("adc", "dma", "runtime"), contracts=("ci_adc_macros",))
def adc_dma(target):
    for sequence in (1, 2):
        target.reach("DMA1_Channel1_IRQHandler")
        target.check("DMA exception", target.value("$xPSR & 0x1ff"), 25)
        target.check("DMA exhausted", target.value("DMA1_Channel1->CNDTR"), 0)
        target.check("transfer complete, no error", target.value("DMA1->ISR & (DMA_ISR_TCIF1 | DMA_ISR_TEIF1)"), 2)
        raw = [target.value(f"board_adc_buffer[{i}]") for i in range(2)]
        target.reach("board_delay_ms")
        target.check("published sequence", target.value("board_adc_sequences"), sequence)
        for name, expected in zip(("board_temperature_raw", "board_reference_raw"), raw):
            target.check(name + " published", target.value(name), expected)
            target.check(name + " not saturated", 0 < expected < 4095, True)
        target.check("no ADC overrun", target.value("ADC1->ISR & ADC_ISR_OVR"), 0)
        target.check("no acquisition error", target.value("board_adc_error"), 0)


@case("HW_CI_ADC_TIMEOUT", labels=("adc", "dma", "negative"), contracts=("ci_adc_macros",))
def adc_timeout(target):
    target.reach("board_adc_sample")
    target.set_value("NVIC->ICER[0]", 1 << 9)
    target.reach("board_adc_fault")
    target.check("completion deadline", target.value("board_adc_error"), 4)
    target.check("no stale publication", target.value("board_adc_sequences"), 0)
    target.check("DMA finished despite missing IRQ", target.value("DMA1_Channel1->CNDTR"), 0)


@case("HW_CI_ADC_UNITS", labels=("adc", "units"), contracts=("ci_adc_units",))
def adc_units(target):
    target.reach("board_adc_sample")
    target.reach("board_delay_ms")
    target.check("single-point provenance", target.value("board_adc_reading.quality"), 3)
    target.check("plausible VDDA", 2800 <= target.value("board_adc_reading.vdda_mv") <= 3600, True)
    target.check("plausible die temperature", -40000 <= target.value("board_adc_reading.temperature_mdeg_c") <= 125000, True)
    target.report["measurement"] = {field: target.value("board_adc_reading." + field)
                                    for field in ("vdda_mv", "temperature_mdeg_c", "quality")}


def check_conversion(target, inputs, expected):
    target.reach("adc_convert_f030")
    for name, value in zip(("temperature", "reference", "reference_cal", "temperature_cal"), inputs):
        target.set_value(name, value)
    target.reach("board_delay_ms")
    target.fields("board_adc_reading", dict(zip(("vdda_mv", "temperature_mdeg_c", "quality"), expected)))


@case("HW_CI_ADC_VECTORS", timeout_s=60, labels=("adc", "arithmetic"), contracts=("ci_adc_units",))
def adc_vectors(target):
    # Fixed analytic anchors; expected values are not computed using firmware code.
    for inputs, expected in (
        ((1800, 1500, 1500, 1800), (3300, 30000, 3)),
        ((1980, 1650, 1500, 1800), (3000, 30000, 3)),
        ((1700, 1500, 1500, 1800), (3300, 48740, 3)),
        ((1900, 1500, 1500, 1800), (3300, 11260, 3)),
        ((2200, 1500, 1500, 1800), (3300, -44963, 3)),
        ((2475, 1650, 1200, 1800), (2400, 30000, 3)),
        ((1650, 1650, 1800, 1800), (3600, 30000, 3)),
    ):
        check_conversion(target, inputs, expected)


@case("HW_CI_ADC_INVALID", timeout_s=60, labels=("adc", "negative", "arithmetic"), contracts=("ci_adc_units",))
def adc_invalid(target):
    for index in range(4):
        for invalid in (0, 4095, 65535):
            inputs = [1800, 1500, 1500, 1800]
            inputs[index] = invalid
            check_conversion(target, inputs, (0, 0, 0))
    for reference in (1, 4094):
        check_conversion(target, (1800, reference, 1500, 1800), (0, 0, 0))
    # A subsequent normal acquisition replaces the invalid result.
    target.reach("board_adc_sample")
    target.reach("board_delay_ms")
    target.check("measurement recovers", target.value("board_adc_reading.quality"), 3)
