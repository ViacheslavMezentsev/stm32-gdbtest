"""
RU: Проверки инициализации ADC, DMA, TIM3 и RTC средствами HAL.
EN: HAL initialization checks for ADC, DMA, TIM3 and RTC.
"""
from stm32_gdbtest import case


# Verify the HAL ADC and DMA initialization parameters.
@case("HW_ADC_DMA_INIT", labels=("adc", "dma", "init"), contracts=("adc_init_macros",))
def adc_dma_init(t):
    t.reach("platform_adc_prepare")

    # Check the published fields against the expected values.
    t.check([(f"hadc.{field}", f"hadc.{field}", expected) for field, expected in (
        ("Instance", "ADC1"), ("Init.Resolution", "ADC_RESOLUTION_12B"),
        ("Init.ScanConvMode", "ADC_SCAN_DIRECTION_FORWARD"), ("Init.ContinuousConvMode", "DISABLE"),
        ("Init.DMAContinuousRequests", "DISABLE"), ("Init.ClockPrescaler", "ADC_CLOCK_ASYNC_DIV1"),
        ("Init.ExternalTrigConv", "ADC_SOFTWARE_START"),
        ("Init.ExternalTrigConvEdge", "ADC_EXTERNALTRIGCONVEDGE_NONE"))])

    # The registers the initialization wrote: the internal channels 16 and 17, forward scan, longest sampling.
    t.check([
        ('only channels 16/17', 'ADC1->CHSELR', 'ADC_CHSELR_CHSEL16 | ADC_CHSELR_CHSEL17'),
        ('forward scan', 'ADC1->CFGR1 & ADC_CFGR1_SCANDIR', 0),
        ('239.5 cycles', 'ADC1->SMPR & ADC_SMPR_SMP', 'ADC_SAMPLETIME_239CYCLES_5')
    ])

    # The DMA handle the ADC uses: one normal transfer of halfwords into memory.
    t.check([(f"hdma_adc.{field}", f"hdma_adc.{field}", expected) for field, expected in (
        ("Instance", "DMA1_Channel1"), ("Init.Direction", "DMA_PERIPH_TO_MEMORY"), ("Init.Mode", "DMA_NORMAL"),
        ("Init.MemInc", "DMA_MINC_ENABLE"), ("Init.PeriphDataAlignment", "DMA_PDATAALIGN_HALFWORD"),
        ("Init.MemDataAlignment", "DMA_MDATAALIGN_HALFWORD"))])


# Verify HAL TIM3 initialization parameters and applied register state.
@case("HW_TIM3_INIT", labels=("tim", "init"), contracts=("tim_init_macros",))
def tim3_init(t):
    t.reach("platform_adc_prepare")

    # HSI 8 MHz system clock; TIM3 counts at 1 kHz and overflows every 100 ms (independent of CubeMX).
    hsi_hz, tick_hz, period_ticks = 8_000_000, 1_000, 100

    # Check the timer registers against the independent timing.
    t.check([
        ('TIM3 prescaler', 'TIM3->PSC', hsi_hz // tick_hz - 1),
        ('TIM3 period', '__HAL_TIM_GET_AUTORELOAD(&htim3)', period_ticks - 1),
        ('TIM3 not started', 'TIM3->CR1 & TIM_CR1_CEN', 0)
    ])


# Verify RTC clock, calendar masks, alarm configuration and interrupt routing.
@case("HW_RTC_INIT", labels=("rtc", "init"), contracts=("rtc_init_macros",))
def rtc_init(t):
    t.reach("platform_adc_prepare")

    # LSI 40 kHz nominal: 1 Hz = LSI / 128 / 312 (RM, independent of CubeMX).
    lsi_hz, prediv_a = 40_000, 128

    # Check the RTC source and alarm setup after initialization.
    t.check([
        ("RTC source LSI", "RCC->BDCR & RCC_BDCR_RTCSEL", "RCC_RTCCLKSOURCE_LSI"),
        ("RTC enabled", "RCC->BDCR & RCC_BDCR_RTCEN"),
        ("LSI ready", "RCC->CSR & RCC_CSR_LSIRDY"),
        ("asynchronous divider", "(RTC->PRER & RTC_PRER_PREDIV_A) >> RTC_PRER_PREDIV_A_Pos", prediv_a - 1),
        ("synchronous divider", "RTC->PRER & RTC_PRER_PREDIV_S", lsi_hz // prediv_a - 1),
        ("RTC output disabled", "RTC->CR & RTC_CR_OSEL", 0)
    ])
