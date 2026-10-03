"""TECH-010 paired research variants; original board scenarios unchanged."""
from table_checks import check_values

F030_RTC = [
    ('LSI ready', '(RCC->CSR & RCC_CSR_LSIRDY) != 0', 1),
    ('LSI RTC clock enabled', 'RCC->BDCR & (RCC_BDCR_RTCSEL | RCC_BDCR_RTCEN)', 33280),
    ('RTC prescalers', 'RTC->PRER', 127 << 16 | 311),
    ('24-hour Alarm A enabled with IRQ', 'RTC->CR', 4352),
    ('all calendar fields masked', 'RTC->ALRMAR', 2155905152),
    ('subseconds masked', 'RTC->ALRMASSR', 0),
    ('initialization completed', 'RTC->ISR & RTC_ISR_INIT', 0),
    ('shadow synchronized', '(RTC->ISR & RTC_ISR_RSF) != 0', 1),
    ('EXTI17 enabled rising edge', '(EXTI->IMR & EXTI->RTSR) & (1 << 17)', 1 << 17),
    ('EXTI17 falling edge off', 'EXTI->FTSR & (1 << 17)', 0),
    ('RTC NVIC enabled', 'NVIC->ISER[0] & (1 << 2)', 1 << 2),
    ('RTC vector', '(unsigned int)vectors[18] & ~1U', '(unsigned int)RTC_IRQHandler & ~1U'),
    ('no RTC error', 'board_rtc_error', 0),
]

def f030_rtc(target):
    target.reach('board_led_toggle')
    check_values(target, F030_RTC)

F411_ADC = [
    ('ADC1 clock', '(RCC->APB2ENR & RCC_APB2ENR_ADC1EN) != 0', 1),
    ('DMA2 clock', '(RCC->AHB1ENR & RCC_AHB1ENR_DMA2EN) != 0', 1),
    ('ADC clock PCLK2/2 (8 MHz)', 'ADC->CCR & ADC_CCR_ADCPRE', 0),
    ('scan only, independent ADC', 'ADC1->CR1', 256),
    ('ADC enabled, internal sources, DMA, software trigger', 'ADC1->CR2', 769),
    ('sample CH18/17 at 480 cycles', 'ADC1->SMPR1', 132120576),
    ('two regular ranks', 'ADC1->SQR1', 1 << 20),
    ('CH18 then CH17', 'ADC1->SQR3', 18 | 17 << 5),
    ('normal DMA halfwords, TC/TE/DME IRQ', 'DMA2_Stream0->CR', 11286),
    ('ADC data address', 'DMA2_Stream0->PAR', '&ADC1->DR'),
    ('SRAM buffer address', 'DMA2_Stream0->M0AR', '&board_adc_buffer[0]'),
    ('DMA NVIC enabled', '(NVIC->ISER[1] >> 24) & 1', 1),
    ('DMA vector', '(unsigned int)vectors[72] & ~1U', '(unsigned int)DMA2_Stream0_IRQHandler & ~1U'),
    ('internal sources without VBAT', 'ADC->CCR', 1 << 23),
    ('direct DMA mode', 'DMA2_Stream0->FCR & 0x84', 0),
    ('no init error', 'board_adc_error', 0),
]

def f411_adc(t):
    t.reach('board_adc_sample')
    check_values(t, F411_ADC)

F103_TIMER = [
    ('TIM2 clock', '(RCC->APB1ENR & RCC_APB1ENR_TIM2EN) != 0', 1),
    ('TIM2 prescaler', 'TIM2->PSC', 7999),
    ('TIM2 period', 'TIM2->ARR', 99),
    ('TIM2 internal clock', 'TIM2->SMCR', 0),
    ('TIM2 upcounter enabled', 'TIM2->CR1', 1),
    ('update interrupt only', 'TIM2->DIER', 1),
    ('NVIC TIM2 enabled', '(NVIC->ISER[0] >> 28) & 1', 1),
    ('TIM2 vector', '(unsigned int)vectors[44] & ~1U', '(unsigned int)TIM2_IRQHandler & ~1U'),
]

def f103_timer(target):
    target.reach('board_led_toggle')
    check_values(target, F103_TIMER)
