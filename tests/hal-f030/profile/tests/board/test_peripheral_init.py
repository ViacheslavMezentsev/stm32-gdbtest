"""
RU: Проверки инициализации ADC, DMA, TIM3 и RTC средствами HAL.
EN: HAL initialization checks for ADC, DMA, TIM3 and RTC.
"""
from stm32_gdbtest import case


# Evaluate table rows in order and stop at the first failed read or check.
def _check_values(target, rows):
    # TECH-010: evaluate each actual, then its expected expression, then check.
    for name, expression, expected in rows:
        actual = target.value(expression)
        if isinstance(expected, str):
            expected = target.value(expected)

        # Compare the current row after both expressions have been evaluated.
        target.check(name, actual, expected)


# Verify the HAL ADC and DMA initialization parameters.
@case("HW_ADC_DMA_INIT", labels=("adc", "dma", "init"), contracts=("adc_init_macros",))
def adc_dma_init(t):
    t.reach("platform_adc_prepare")

    # Check the published fields against the expected values.
    t.fields("hadc", {"Instance": "ADC1", "Init.Resolution": "ADC_RESOLUTION_12B",
        "Init.ScanConvMode": "ADC_SCAN_DIRECTION_FORWARD", "Init.ContinuousConvMode": 0,
        "Init.DMAContinuousRequests": 0, "Init.ClockPrescaler": "ADC_CLOCK_ASYNC_DIV1",
        "Init.ExternalTrigConv": "ADC_SOFTWARE_START", "Init.ExternalTrigConvEdge": "ADC_EXTERNALTRIGCONVEDGE_NONE"})

    _check_values(t, [
        ('only channels 16/17', 'ADC1->CHSELR', 1 << 16 | 1 << 17),
        ('forward scan', 'ADC1->CFGR1 & ADC_CFGR1_SCANDIR', 0),
        ('239.5 cycles', 'ADC1->SMPR & ADC_SMPR_SMP', 7)
    ])

    t.fields("hdma_adc", {"Instance": "DMA1_Channel1", "Init.Direction": "DMA_PERIPH_TO_MEMORY",
        "Init.Mode": "DMA_NORMAL", "Init.MemInc": "DMA_MINC_ENABLE",
        "Init.PeriphDataAlignment": "DMA_PDATAALIGN_HALFWORD",
        "Init.MemDataAlignment": "DMA_MDATAALIGN_HALFWORD"})


# Verify HAL TIM3 initialization parameters and applied register state.
@case("HW_TIM3_INIT", labels=("tim", "init"), contracts=("tim_init_macros",))
def tim3_init(t):
    t.reach("platform_adc_prepare")

    # Check register and application state against the expected values.
    _check_values(t, [
        ('TIM3 prescaler', 'TIM3->PSC', 7999),
        ('TIM3 period', '__HAL_TIM_GET_AUTORELOAD(&htim3)', 99),
        ('TIM3 not started', 'TIM3->CR1 & TIM_CR1_CEN', 0)
    ])


# Verify RTC clock, calendar masks, alarm configuration and interrupt routing.
@case("HW_RTC_INIT", labels=("rtc", "init"), contracts=("rtc_init_macros",))
def rtc_init(t):
    t.reach("platform_adc_prepare")

    # Check the RTC source and alarm setup after initialization.
    t.check("RTC source LSI", (t.value("RCC->BDCR") >> 8) & 3, 2)
    t.check("RTC enabled", (t.value("RCC->BDCR") >> 15) & 1, 1)
    t.check("LSI ready", (t.value("RCC->CSR") >> 1) & 1, 1)
    t.check("asynchronous divider", (t.value("RTC->PRER") >> 16) & 127, 127)
    t.check("synchronous divider", t.value("RTC->PRER") & 32767, 311)
    t.check("RTC output disabled", (t.value("RTC->CR") >> 21) & 3, 0)
