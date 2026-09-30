"""F030R8 expectations from IOC/CMSIS/RM0360; validated via J-Link STLink/SWD."""
EXPECTED = {
    "clock": [
        ("HSI", "(RCC->CFGR & RCC_CFGR_SWS_Msk) >> RCC_CFGR_SWS_Pos", 0),
        ("AHB /1", "(RCC->CFGR & RCC_CFGR_HPRE_Msk) >> RCC_CFGR_HPRE_Pos", 0),
        ("APB /1", "(RCC->CFGR & RCC_CFGR_PPRE_Msk) >> RCC_CFGR_PPRE_Pos", 0),
        ("ADC clock", "__HAL_RCC_ADC1_IS_CLK_ENABLED()", 1),
        ("TIM3 clock", "__HAL_RCC_TIM3_IS_CLK_ENABLED()", 1),
        ("DMA clock", "__HAL_RCC_DMA1_IS_CLK_ENABLED()", 1)],
    "gpio": [
        ("GPIOA clock", "__HAL_RCC_GPIOA_IS_CLK_ENABLED()", 1),
        ("PA5 output", "(GPIOA->MODER >> 10) & 3", 1),
        ("PA5 push-pull", "(GPIOA->OTYPER >> 5) & 1", 0),
        ("PA5 no pull", "(GPIOA->PUPDR >> 10) & 3", 0),
        ("PA5 low speed", "(GPIOA->OSPEEDR >> 10) & 3", 0),
        ("PA5 initially off", "(GPIOA->ODR >> 5) & 1", 0)],
    "led_initial": 0,
    "led_level": "(GPIOA->ODR >> 5) & 1",
    "adc_handle": "hadc",
    "timer_handle": "htim3",
    "timer_enabled": "TIM3->CR1 & TIM_CR1_CEN",
    "dma_remaining": "DMA1_Channel1->CNDTR",
    "measurement_quality": 3,
    # One factory temperature anchor; voltage/temperature accuracy is not measured.
    "adc_vectors": [("*(unsigned short *)0x1FFFF7B8", "*(unsigned short *)0x1FFFF7BA", 3300, 30000)],
}
