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
        ('PA5 clock', '(RCC->AHBENR & RCC_AHBENR_GPIOAEN) != 0', 1),
        ('PA5 output', '(GPIOA->MODER & GPIO_MODER_MODER5) == GPIO_MODER_MODER5_0', 1),
        ('push-pull', 'GPIOA->OTYPER & GPIO_OTYPER_OT_5', 0),
        ('low speed', 'GPIOA->OSPEEDR & GPIO_OSPEEDR_OSPEEDR5', 0),
        ('no pull', 'GPIOA->PUPDR & GPIO_PUPDR_PUPDR5', 0),
        ('initial LED off', 'GPIOA->ODR & GPIO_ODR_5', 0),
    ])


@case("HW_CI_CLOCK", labels=("clock",), contracts=("ci_clock_macros",))
def clock(target):
    # TECH-001: docs/ru/TESTING_TECHNIQUES.md#tech-001 (EN: docs/en/TESTING_TECHNIQUES.md#tech-001).
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
    _check_values(target, [
        ('TIM3 clock', '(RCC->APB1ENR & RCC_APB1ENR_TIM3EN) != 0', 1),
        ('TIM3 prescaler', 'TIM3->PSC', 7999),
        ('TIM3 period', 'TIM3->ARR', 99),
        ('TIM3 internal clock', 'TIM3->SMCR', 0),
        ('TIM3 upcounter enabled', 'TIM3->CR1', 1),
        ('update interrupt only', 'TIM3->DIER', 1),
        ('NVIC TIM3 enabled', '(NVIC->ISER[0] >> 16) & 1', 1),
        ('TIM3 vector', '(unsigned int)vectors[32] & ~1U', '(unsigned int)TIM3_IRQHandler & ~1U'),
    ])


@case("HW_CI_TIM3_IRQ", labels=("timer", "irq"), contracts=("ci_timer_macros",))
def timer_irq(target):
    # Run to actual exception entries, without EGR/NVIC/software injection.
    target.reach("TIM3_IRQHandler")
    for _ in range(2):
        target.check("TIM3 exception number", target.value("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 32)
        target.check("update pending", target.value("TIM3->SR & TIM_SR_UIF"), 1)
        before = target.value("board_timer_events")
        target.reach("TIM3_IRQHandler")
        target.check("one event published", target.value("board_timer_events"), (before + 1) & 0xFFFFFFFF)
    # A permanently asserted update IRQ would starve thread mode on this M0.
    target.reach("board_delay_ms")
    target.check("thread mode resumes", target.value("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 0)


@case("HW_CI_ADC_INIT", labels=("adc", "dma", "init"), contracts=("ci_adc_macros",))
def adc_init(target):
    target.reach("board_adc_sample")
    _check_values(target, [
        ('HSI14 ready', '(RCC->CR2 & RCC_CR2_HSI14RDY) != 0', 1),
        ('ADC clock', '(RCC->APB2ENR & RCC_APB2ENR_ADC1EN) != 0', 1),
        ('DMA clock', '(RCC->AHBENR & RCC_AHBENR_DMA1EN) != 0', 1),
        ('async ADC clock', 'ADC1->CFGR2 & ADC_CFGR2_CKMODE', 0),
        ('forward single 12bit scan', 'ADC1->CFGR1', 0),
        ('channels16/17', 'ADC1->CHSELR', 1 << 16 | 1 << 17),
        ('239.5 sample cycles', 'ADC1->SMPR', 7),
        ('internal paths', 'ADC1_COMMON->CCR & (ADC_CCR_TSEN | ADC_CCR_VREFEN)', 1 << 23 | 1 << 22),
        ('calibration finished, ADC enabled', 'ADC1->CR & (ADC_CR_ADCAL | ADC_CR_ADEN)', 1),
        ('DMA normal halfwords, increment, TC/TE IRQ', 'DMA1_Channel1->CCR', 1418),
        ('DMA peripheral address', 'DMA1_Channel1->CPAR', '&ADC1->DR'),
        ('DMA SRAM buffer', 'DMA1_Channel1->CMAR', '&board_adc_buffer[0]'),
        ('DMA NVIC enabled', '(NVIC->ISER[0] >> 9) & 1', 1),
        ('DMA vector', '(unsigned int)vectors[25] & ~1U', '(unsigned int)DMA1_Channel1_IRQHandler & ~1U'),
        ('no init error', 'board_adc_error', 0),
    ])


@case("HW_CI_ADC_DMA", labels=("adc", "dma", "runtime"), contracts=("ci_adc_macros",))
def adc_dma(target):
    for sequence in (1, 2):
        target.reach("DMA1_Channel1_IRQHandler")
        _check_values(target, [
            ('DMA exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 25),
            ('DMA exhausted', 'DMA1_Channel1->CNDTR', 0),
            ('transfer complete, no error', 'DMA1->ISR & (DMA_ISR_TCIF1 | DMA_ISR_TEIF1)', 2),
        ])
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
    # TECH-006: docs/ru/TESTING_TECHNIQUES.md#tech-006 (EN: docs/en/TESTING_TECHNIQUES.md#tech-006).
    target.reach("board_adc_sample")
    target.set_value("NVIC->ICER[0]", 1 << 9)
    target.reach("board_adc_fault")
    _check_values(target, [
        ('completion deadline', 'board_adc_error', 4),
        ('no stale publication', 'board_adc_sequences', 0),
        ('DMA finished despite missing IRQ', 'DMA1_Channel1->CNDTR', 0),
    ])


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
    # TECH-007: docs/ru/TESTING_TECHNIQUES.md#tech-007 (EN: docs/en/TESTING_TECHNIQUES.md#tech-007).
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
