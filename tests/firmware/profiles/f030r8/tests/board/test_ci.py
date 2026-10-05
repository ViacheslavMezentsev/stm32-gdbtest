"""
RU: Проверки запуска, GPIO, тактирования и периферии платы.
EN: Board startup, GPIO, clock and peripheral checks.
"""
from stm32_gdbtest import case, within


# Full scale of the 12-bit ADC: 0 and 4095 are saturated readings.
ADC_FULL_SCALE = 4095

# Plausibility windows of a reading; not a calibration or accuracy claim.
PLAUSIBLE_VDDA_MV = within(2800, 3600)
PLAUSIBLE_DIE_MDEG_C = within(-40_000, 125_000)

# Provenance of a published reading (adc_units.c): 0 invalid, 1 typical datasheet values,
# 2 factory two-point calibration, 3 factory one-point calibration.
QUALITY_INVALID = 0
QUALITY_ONE_POINT = 3
# board_adc_error codes of the fixture firmware (adc_*.c).
ADC_ERROR_NONE = 0
ADC_ERROR_DEADLINE = 4

# HSI is the system clock of the fixture (RM: 8 MHz nominal).
HSI_HZ = 8_000_000
# TIM3 counts at 1 kHz and overflows every 100 ms.
TIMER_TICK_HZ = 1_000
TIMER_PERIOD_TICKS = 100

# Firmware counters are uint32_t and wrap around.
U32_MASK = 0xFFFFFFFF

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
        ('PA5 clock', 'RCC->AHBENR & RCC_AHBENR_GPIOAEN'),
        ('PA5 output', '(GPIOA->MODER & GPIO_MODER_MODER5) == GPIO_MODER_MODER5_0', 1),
        ('push-pull', 'GPIOA->OTYPER & GPIO_OTYPER_OT_5', 0),
        ('low speed', 'GPIOA->OSPEEDR & GPIO_OSPEEDR_OSPEEDR5', 0),
        ('no pull', 'GPIOA->PUPDR & GPIO_PUPDR_PUPDR5', 0),
        ('initial LED off', 'GPIOA->ODR & GPIO_ODR_5', 0)
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
        ("HSI enabled and ready", "RCC->CR & (RCC_CR_HSION | RCC_CR_HSIRDY)", "RCC_CR_HSION | RCC_CR_HSIRDY"),
        ("SYSCLK HSI, AHB/APB divide by one",
         "RCC->CFGR & (RCC_CFGR_SW | RCC_CFGR_SWS | RCC_CFGR_HPRE | RCC_CFGR_PPRE)", 0),
        ("nominal core frequency", "SystemCoreClock", HSI_HZ),
        ("1 ms reload at nominal 8 MHz", "SysTick->LOAD", HSI_HZ // 1000 - 1),
        ("SysTick enabled, interrupt, core clock", f"SysTick->CTRL & ({systick_running})", systick_running)
    ])


# Observe consecutive LED transitions and their firmware timing.
@case("HW_CI_BLINK", labels=("gpio", "timing"), contracts=("ci_gpio_macros",))
def blink(t):
    t.reach("board_led_toggle")

    # Verify initial Low.
    t.check("initial Low", t.read("(GPIOA->ODR & GPIO_ODR_5) != 0"), 0)

    before = t.read("board_ticks_ms")

    # Observe alternating output levels and check the elapsed firmware ticks.
    for level in (1, 0):
        t.reach("board_led_toggle")
        now = t.read("board_ticks_ms")

        # Check alternating output levels and the minimum firmware interval.
        t.check("alternating PA5", t.read("(GPIOA->ODR & GPIO_ODR_5) != 0"), level)
        t.check("at least the configured interval", ((now - before) & U32_MASK) >= EXPECTED_DELAY)

        before = now


# Verify timer clock, counter configuration and interrupt routing.
@case("HW_CI_TIM3_INIT", labels=("timer", "init"), contracts=("ci_timer_macros",))
def timer_init(t):
    t.reach("board_led_toggle")

    # Check register and application state against the expected values.
    t.check([
        ('TIM3 clock', 'RCC->APB1ENR & RCC_APB1ENR_TIM3EN'),
        ('TIM3 prescaler', 'TIM3->PSC', HSI_HZ // TIMER_TICK_HZ - 1),
        ('TIM3 period', 'TIM3->ARR', TIMER_PERIOD_TICKS - 1),
        ('TIM3 internal clock', 'TIM3->SMCR', 0),
        ('TIM3 upcounter enabled', 'TIM3->CR1', 'TIM_CR1_CEN'),
        ('update interrupt only', 'TIM3->DIER', 'TIM_DIER_UIE'),
        ('NVIC TIM3 enabled', 'NVIC->ISER[TIM3_IRQn >> 5] & (1UL << (TIM3_IRQn & 31))'),
        ('TIM3 vector', '(unsigned int)vectors[TIM3_IRQn + 16] & ~1U', '(unsigned int)TIM3_IRQHandler & ~1U')
    ])


# Observe timer interrupt handling and advancement of the event counter.
@case("HW_CI_TIM3_IRQ", labels=("timer", "irq"), contracts=("ci_timer_macros",))
def timer_irq(t):
    # Run to actual exception entries, without EGR/NVIC/software injection.
    t.reach("TIM3_IRQHandler")

    # Observe consecutive timer interrupts and the event counter between them.
    for _ in range(2):
        # Check the active timer exception and pending update flag.
        t.check("TIM3 exception number", t.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), t.evaluate("TIM3_IRQn + 16"))
        t.check("update pending", t.read("TIM3->SR & TIM_SR_UIF"), t.evaluate("TIM_SR_UIF"))

        before = t.read("board_timer_events")
        t.reach("TIM3_IRQHandler")

        # Verify one event published.
        t.check("one event published", t.read("board_timer_events"), (before + 1) & U32_MASK)

    # A permanently asserted update IRQ would starve thread mode on this M0.
    t.reach("board_delay_ms")

    # Verify thread mode resumes.
    t.check("thread mode resumes", t.read("SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk"), 0)


# Verify ADC channels, sampling configuration, DMA and interrupt routing.
@case("HW_CI_ADC_INIT", labels=("adc", "dma", "init"), contracts=("ci_adc_macros",))
def adc_init(t):
    t.reach("board_adc_sample")

    # Check register and application state against the expected values.
    t.check([
        ('HSI14 ready', 'RCC->CR2 & RCC_CR2_HSI14RDY'),
        ('ADC clock', 'RCC->APB2ENR & RCC_APB2ENR_ADC1EN'),
        ('DMA clock', 'RCC->AHBENR & RCC_AHBENR_DMA1EN'),
        ('async ADC clock', 'ADC1->CFGR2 & ADC_CFGR2_CKMODE', 0),
        ('forward single 12bit scan', 'ADC1->CFGR1', 0),
        ('channels16/17', 'ADC1->CHSELR', 'ADC_CHSELR_CHSEL16 | ADC_CHSELR_CHSEL17'),
        ('239.5 sample cycles', 'ADC1->SMPR', 'ADC_SMPR_SMP'),
        ('internal paths', 'ADC1_COMMON->CCR & (ADC_CCR_TSEN | ADC_CCR_VREFEN)', 'ADC_CCR_TSEN | ADC_CCR_VREFEN'),
        ('calibration finished, ADC enabled', 'ADC1->CR & (ADC_CR_ADCAL | ADC_CR_ADEN)', 'ADC_CR_ADEN'),
        ('DMA normal halfwords, increment, TC/TE IRQ', 'DMA1_Channel1->CCR',
         'DMA_CCR_MINC | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_0 | DMA_CCR_TCIE | DMA_CCR_TEIE'),
        ('DMA peripheral address', 'DMA1_Channel1->CPAR', '&ADC1->DR'),
        ('DMA SRAM buffer', 'DMA1_Channel1->CMAR', '&board_adc_buffer[0]'),
        ('DMA NVIC enabled', 'NVIC->ISER[DMA1_Channel1_IRQn >> 5] & (1UL << (DMA1_Channel1_IRQn & 31))'),
        ('DMA vector', '(unsigned int)vectors[DMA1_Channel1_IRQn + 16] & ~1U',
         '(unsigned int)DMA1_Channel1_IRQHandler & ~1U'),
        ('no init error', 'board_adc_error', ADC_ERROR_NONE)
    ])


# Observe completed DMA transfers and validate the published ADC samples.
@case("HW_CI_ADC_DMA", labels=("adc", "dma", "runtime"), contracts=("ci_adc_macros",))
def adc_dma(t):
    # Follow successive DMA publications and compare raw and published samples.
    for sequence in (1, 2):
        t.reach("DMA1_Channel1_IRQHandler")

        # Check register and application state against the expected values.
        t.check([
            ('DMA exception', 'SCB->ICSR & SCB_ICSR_VECTACTIVE_Msk', 'DMA1_Channel1_IRQn + 16'),
            ('DMA exhausted', 'DMA1_Channel1->CNDTR', 0),
            ('transfer complete, no error', 'DMA1->ISR & (DMA_ISR_TCIF1 | DMA_ISR_TEIF1)', 'DMA_ISR_TCIF1')
        ])

        raw = [t.read(f"board_adc_buffer[{i}]") for i in range(2)]
        t.reach("board_delay_ms")

        # Check the publication counter before comparing measurement contents.
        t.check("published sequence", t.read("board_adc_sequences"), sequence)

        # Compare each published channel with its captured DMA value and reject saturation.
        for name, expected in zip(("board_temperature_raw", "board_reference_raw"), raw):
            # Verify the current sample against its expected value and validity bounds.
            t.check(name + " published", t.read(name), expected)
            t.check(name + " not saturated", 0 < expected < ADC_FULL_SCALE)

        # Check that acquisition completed without peripheral errors.
        t.check("no ADC overrun", t.read("ADC1->ISR & ADC_ISR_OVR"), 0)
        t.check("no acquisition error", t.read("board_adc_error"), ADC_ERROR_NONE)


# Suppress completion notification and verify the ADC deadline and fault state.
@case("HW_CI_ADC_TIMEOUT", labels=("adc", "dma", "negative"), contracts=("ci_adc_macros",))
def adc_timeout(t):
    # TECH-006: docs/ru/TESTING_TECHNIQUES.md#tech-006 (EN: docs/en/TESTING_TECHNIQUES.md#tech-006).
    t.reach("board_adc_sample")
    irq = t.evaluate("DMA1_Channel1_IRQn")
    t.write(f"NVIC->ICER[{irq >> 5}]", 1 << (irq & 31))
    t.reach("board_adc_fault")

    # Check register and application state against the expected values.
    t.check([
        ('completion deadline', 'board_adc_error', ADC_ERROR_DEADLINE),
        ('no stale publication', 'board_adc_sequences', 0),
        ('DMA finished despite missing IRQ', 'DMA1_Channel1->CNDTR', 0)
    ])


# Check measurement provenance and plausible VDDA and die temperature.
@case("HW_CI_ADC_UNITS", labels=("adc", "units"), contracts=("ci_adc_units",))
def adc_units(t):
    t.reach("board_adc_sample")
    t.reach("board_delay_ms")

    # Check measurement provenance and plausible physical ranges.
    t.check([
        ("single-point provenance", "board_adc_reading.quality", QUALITY_ONE_POINT),
        ("plausible VDDA", "board_adc_reading.vdda_mv", PLAUSIBLE_VDDA_MV),
        ("plausible die temperature", "board_adc_reading.temperature_mdeg_c", PLAUSIBLE_DIE_MDEG_C)
    ])

    t.report["measurement"] = {field: t.read("board_adc_reading." + field)
                               for field in ("vdda_mv", "temperature_mdeg_c", "quality")}


# Inject conversion inputs and compare the published reading with fixed expectations.
def check_conversion(t, inputs, expected):
    t.reach("adc_convert_f030")

    # Replace each conversion argument with the corresponding test input.
    for name, value in zip(("temperature", "reference", "reference_cal", "temperature_cal"), inputs):
        t.write(name, value)

    t.reach("board_delay_ms")

    # Check the published fields against the expected values.
    t.check([(f"board_adc_reading.{field}", f"board_adc_reading.{field}", value)
             for field, value in zip(("vdda_mv", "temperature_mdeg_c", "quality"), expected)])


# Check conversion arithmetic against independent numerical reference vectors.
@case("HW_CI_ADC_VECTORS", timeout_s=60, labels=("adc", "arithmetic"), contracts=("ci_adc_units",))
def adc_vectors(t):
    # TECH-007: docs/ru/TESTING_TECHNIQUES.md#tech-007 (EN: docs/en/TESTING_TECHNIQUES.md#tech-007).
    # Fixed analytic anchors; expected values are not computed using firmware code.
    for inputs, expected in (
        ((1800, 1500, 1500, 1800), (3300, 30000, QUALITY_ONE_POINT)),
        ((1980, 1650, 1500, 1800), (3000, 30000, QUALITY_ONE_POINT)),
        ((1700, 1500, 1500, 1800), (3300, 48740, QUALITY_ONE_POINT)),
        ((1900, 1500, 1500, 1800), (3300, 11260, QUALITY_ONE_POINT)),
        ((2200, 1500, 1500, 1800), (3300, -44963, 3)),
        ((2475, 1650, 1200, 1800), (2400, 30000, QUALITY_ONE_POINT)),
        ((1650, 1650, 1800, 1800), (3600, 30000, QUALITY_ONE_POINT))
    ):
        check_conversion(t, inputs, expected)


# Reject invalid conversion inputs and verify subsequent measurement recovery.
@case("HW_CI_ADC_INVALID", timeout_s=60, labels=("adc", "negative", "arithmetic"), contracts=("ci_adc_units",))
def adc_invalid(t):
    # Exercise invalid inputs individually, then verify that normal acquisition recovers.
    for index in range(4):
        # Exercise invalid inputs individually, then verify that normal acquisition recovers.
        for invalid in (0, 4095, 65535):
            inputs = [1800, 1500, 1500, 1800]
            inputs[index] = invalid
            check_conversion(t, inputs, (0, 0, QUALITY_INVALID))

    # Exercise invalid inputs individually, then verify that normal acquisition recovers.
    for reference in (1, 4094):
        check_conversion(t, (1800, reference, 1500, 1800), (0, 0, QUALITY_INVALID))

    # A subsequent normal acquisition replaces the invalid result.
    t.reach("board_adc_sample")
    t.reach("board_delay_ms")

    # Check that valid acquisition resumes after the injected failures.
    t.check("measurement recovers", t.read("board_adc_reading.quality"), QUALITY_ONE_POINT)
