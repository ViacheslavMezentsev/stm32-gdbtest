/* F030 internal temperature/reference acquisition through CMSIS and normal DMA. */
#include "app.h"
#include "stm32f0xx.h"

extern volatile uint32_t board_ticks_ms;
volatile uint16_t board_adc_buffer[2];
volatile uint16_t board_temperature_raw;
volatile uint16_t board_reference_raw;
volatile uint32_t board_adc_sequences;
volatile uint32_t board_adc_error;

__attribute__( ( noreturn ) ) void board_adc_fault( void )
{
    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
    for ( ;; )
    {
        __WFI();
    }
}

static void adc_deadline( uint32_t start, uint32_t error )
{
    if ( ( uint32_t ) ( board_ticks_ms - start ) >= 20U )
    {
        board_adc_error = error;
        board_adc_fault();
    }
}

void DMA1_Channel1_IRQHandler( void )
{
    const uint32_t flags = DMA1->ISR;
    if ( ( flags & DMA_ISR_TEIF1 ) != 0U )
    {
        DMA1->IFCR      = DMA_IFCR_CGIF1;
        board_adc_error = 5U;
        board_adc_fault();
    }
    if ( ( flags & DMA_ISR_TCIF1 ) != 0U )
    {
        DMA1_Channel1->CCR &= ~DMA_CCR_EN;
        DMA1->IFCR          = DMA_IFCR_CGIF1;
        /* Forward scan CH16 then CH17, published before the completion counter. */
        board_temperature_raw = board_adc_buffer[0];
        board_reference_raw   = board_adc_buffer[1];
        board_adc_sequences++;
    }
}

void board_adc_init( void )
{
    RCC->AHBENR  |= RCC_AHBENR_DMA1EN;
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
    ( void ) RCC->APB2ENR;
    RCC->APB2RSTR  |= RCC_APB2RSTR_ADCRST;
    RCC->APB2RSTR  &= ~RCC_APB2RSTR_ADCRST;
    RCC->CR2       |= RCC_CR2_HSI14ON;
    uint32_t start  = board_ticks_ms;
    while ( ( RCC->CR2 & RCC_CR2_HSI14RDY ) == 0U )
    {
        adc_deadline( start, 1U );
    }
    ADC1->CFGR1 = 0U; /* No DMA request during calibration. */
    ADC1->CFGR2 = 0U; /* Asynchronous HSI14, no divider. */
    ADC1->CR    = ADC_CR_ADCAL;
    start       = board_ticks_ms;
    while ( ( ADC1->CR & ADC_CR_ADCAL ) != 0U )
    {
        adc_deadline( start, 2U );
    }
    /* Two SysTick edges guarantee at least one full ms despite tick phase. */
    board_delay_ms( 2U );
    ADC1->CHSELR      = ADC_CHSELR_CHSEL16 | ADC_CHSELR_CHSEL17;
    ADC1->SMPR        = ADC_SMPR_SMP; /* 239.5 cycles for internal sources. */
    ADC1_COMMON->CCR |= ADC_CCR_TSEN | ADC_CCR_VREFEN;
    board_delay_ms( 2U ); /* Internal sources settle before the first scan. */
    ADC1->ISR = ADC_ISR_ADRDY;
    ADC1->CR  = ADC_CR_ADEN;
    start     = board_ticks_ms;
    while ( ( ADC1->ISR & ADC_ISR_ADRDY ) == 0U )
    {
        adc_deadline( start, 3U );
    }
    DMA1_Channel1->CCR  = DMA_CCR_MINC | DMA_CCR_PSIZE_0 | DMA_CCR_MSIZE_0 | DMA_CCR_TCIE | DMA_CCR_TEIE;
    DMA1_Channel1->CPAR = ( uint32_t ) &ADC1->DR;
    DMA1_Channel1->CMAR = ( uint32_t ) board_adc_buffer;
    DMA1->IFCR          = DMA_IFCR_CGIF1;
    NVIC_ClearPendingIRQ( DMA1_Channel1_IRQn );
    NVIC_SetPriority( DMA1_Channel1_IRQn, 1U );
    NVIC_EnableIRQ( DMA1_Channel1_IRQn );
}

void board_adc_sample( void )
{
    if ( ( ADC1->CR & ADC_CR_ADSTART ) != 0U )
    {
        board_adc_error = 6U;
        board_adc_fault();
    }
    const uint32_t before  = board_adc_sequences;
    DMA1_Channel1->CCR    &= ~DMA_CCR_EN;
    DMA1->IFCR             = DMA_IFCR_CGIF1;
    DMA1_Channel1->CNDTR   = 2U;
    ADC1->ISR              = ADC_ISR_EOC | ADC_ISR_EOS | ADC_ISR_OVR;
    /* Toggle DMAEN to rearm limited ADC DMA requests for the next sequence. */
    ADC1->CFGR1          &= ~ADC_CFGR1_DMAEN;
    ADC1->CFGR1          |= ADC_CFGR1_DMAEN;
    DMA1_Channel1->CCR   |= DMA_CCR_EN;
    const uint32_t start  = board_ticks_ms;
    ADC1->CR             |= ADC_CR_ADSTART;
    while ( board_adc_sequences == before )
    {
        adc_deadline( start, 4U );
        __WFI();
    }
}
