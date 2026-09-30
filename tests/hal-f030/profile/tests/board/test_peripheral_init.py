"""F0 register layout is distinct from F1/F4 programmable ADC ranks."""
from stm32_gdbtest import case


@case("HW_ADC_DMA_INIT", labels=("adc", "dma", "init"), contracts=("adc_init_macros",))
def adc_dma_init(t):
    t.reach("platform_adc_prepare")
    t.fields("hadc", {"Instance": "ADC1", "Init.Resolution": "ADC_RESOLUTION_12B",
        "Init.ScanConvMode": "ADC_SCAN_DIRECTION_FORWARD", "Init.ContinuousConvMode": 0,
        "Init.DMAContinuousRequests": 0, "Init.ClockPrescaler": "ADC_CLOCK_ASYNC_DIV1",
        "Init.ExternalTrigConv": "ADC_SOFTWARE_START", "Init.ExternalTrigConvEdge": "ADC_EXTERNALTRIGCONVEDGE_NONE"})
    t.check("only channels 16/17", t.value("ADC1->CHSELR"), (1 << 16) | (1 << 17))
    t.check("forward scan", t.value("ADC1->CFGR1 & ADC_CFGR1_SCANDIR"), 0)
    t.check("239.5 cycles", t.value("ADC1->SMPR & ADC_SMPR_SMP"), 7)
    t.fields("hdma_adc", {"Instance": "DMA1_Channel1", "Init.Direction": "DMA_PERIPH_TO_MEMORY",
        "Init.Mode": "DMA_NORMAL", "Init.MemInc": "DMA_MINC_ENABLE",
        "Init.PeriphDataAlignment": "DMA_PDATAALIGN_HALFWORD",
        "Init.MemDataAlignment": "DMA_MDATAALIGN_HALFWORD"})


@case("HW_TIM3_INIT", labels=("tim", "init"), contracts=("tim_init_macros",))
def tim3_init(t):
    t.reach("platform_adc_prepare")
    t.check("TIM3 prescaler", t.value("TIM3->PSC"), 7999)
    t.check("TIM3 period", t.value("__HAL_TIM_GET_AUTORELOAD(&htim3)"), 99)
    t.check("TIM3 not started", t.value("TIM3->CR1 & TIM_CR1_CEN"), 0)


@case("HW_RTC_INIT", labels=("rtc", "init"), contracts=("rtc_init_macros",))
def rtc_init(t):
    t.reach("platform_adc_prepare")
    t.check("RTC source LSI", (t.value("RCC->BDCR") >> 8) & 3, 2)
    t.check("RTC enabled", (t.value("RCC->BDCR") >> 15) & 1, 1)
    t.check("LSI ready", (t.value("RCC->CSR") >> 1) & 1, 1)
    t.check("asynchronous divider", (t.value("RTC->PRER") >> 16) & 127, 127)
    t.check("synchronous divider", t.value("RTC->PRER") & 32767, 311)
    t.check("RTC output disabled", (t.value("RTC->CR") >> 21) & 3, 0)
