"""
RU: Ожидаемые параметры платы и независимые векторы измерений.
EN: Board expectations and independent measurement reference vectors.
"""
# Expectations of the HAL fixture by group: check(rows) tables, register expressions and handles.
EXPECTED = {
    "clock": [
        ("HSI", "(RCC->CFGR & RCC_CFGR_SWS_Msk) >> RCC_CFGR_SWS_Pos", 0),
        ("AHB /1", "(RCC->CFGR & RCC_CFGR_HPRE_Msk) >> RCC_CFGR_HPRE_Pos", 0),
        ("APB /1", "(RCC->CFGR & RCC_CFGR_PPRE_Msk) >> RCC_CFGR_PPRE_Pos", 0),
        ("ADC clock", "__HAL_RCC_ADC1_IS_CLK_ENABLED()"),
        ("TIM3 clock", "__HAL_RCC_TIM3_IS_CLK_ENABLED()"),
        ("DMA clock", "__HAL_RCC_DMA1_IS_CLK_ENABLED()")],
    "gpio": [
        ("GPIOA clock", "__HAL_RCC_GPIOA_IS_CLK_ENABLED()"),
        ("PA5 output", "GPIOA->MODER & GPIO_MODER_MODER5", "GPIO_MODER_MODER5_0"),
        ("PA5 push-pull", "GPIOA->OTYPER & GPIO_OTYPER_OT_5", 0),
        ("PA5 no pull", "GPIOA->PUPDR & GPIO_PUPDR_PUPDR5", 0),
        ("PA5 low speed", "GPIOA->OSPEEDR & GPIO_OSPEEDR_OSPEEDR5", 0),
        ("PA5 initially off", "GPIOA->ODR & GPIO_ODR_5", 0)],
    "led_initial": 0,
    "led_level": "(GPIOA->ODR & GPIO_ODR_5) != 0",
    "adc_handle": "hadc",
    "timer_handle": "htim3",
    "timer_enabled": "TIM3->CR1 & TIM_CR1_CEN",
    "dma_remaining": "DMA1_Channel1->CNDTR",

    # 3: factory one-point calibration (adc_units provenance code).
    "measurement_quality": 3,

    # One factory temperature anchor (TS_CAL1 at 0x1FFFF7B8, VREFINT_CAL at 0x1FFFF7BA, RM0360);
    # voltage/temperature accuracy is not measured.
    "adc_vectors": [("*(unsigned short *)0x1FFFF7B8", "*(unsigned short *)0x1FFFF7BA", 3300, 30000)]
}
