/* F103 internal temperature/reference: regular scan and normal DMA, no HAL. */
#include "app.h"
#include "adc_units.h"
#include "stm32f1xx.h"

extern volatile uint32_t board_ticks_ms;
volatile uint16_t board_adc_buffer[2];
volatile uint16_t board_temperature_raw;
volatile uint16_t board_reference_raw;
volatile uint32_t board_adc_sequences;
volatile uint32_t board_adc_error;
volatile adc_reading_t board_adc_reading;

__attribute__( ( noreturn ) ) void board_adc_fault( void )
{
    DMA1_Channel1->CCR &= ~DMA_CCR_EN;
    ADC1->CR2          &= ~ADC_CR2_ADON;
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
        DMA1_Channel1->CCR    &= ~DMA_CCR_EN;
        DMA1->IFCR             = DMA_IFCR_CGIF1;
        board_temperature_raw  = board_adc_buffer[0];
        board_reference_raw    = board_adc_buffer[1];
        board_adc_sequences++;
    }
}

void board_adc_init( void )
{
    RCC->AHBENR  |= RCC_AHBENR_DMA1EN;
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
    ( void ) RCC->APB2ENR;
    RCC->APB2RSTR |= RCC_APB2RSTR_ADC1RST;
    RCC->APB2RSTR &= ~RCC_APB2RSTR_ADC1RST;
    RCC->CFGR     &= ~RCC_CFGR_ADCPRE; /* PCLK2 / 2 = 4 MHz. */
    ADC1->CR1      = ADC_CR1_SCAN;
    ADC1->CR2      = ADC_CR2_ADON;
    board_delay_ms( 2U ); /* Power-up and at least two ADC clocks before reset calibration. */
    ADC1->CR2      |= ADC_CR2_RSTCAL;
    uint32_t start  = board_ticks_ms;
    while ( ( ADC1->CR2 & ADC_CR2_RSTCAL ) != 0U )
    {
        adc_deadline( start, 1U );
    }
    ADC1->CR2 |= ADC_CR2_CAL;
    start      = board_ticks_ms;
    while ( ( ADC1->CR2 & ADC_CR2_CAL ) != 0U )
    {
        adc_deadline( start, 2U );
    }
    ADC1->SMPR1 = ADC_SMPR1_SMP16 | ADC_SMPR1_SMP17; /* 239.5 ADC cycles. */
    ADC1->SQR1  = ADC_SQR1_L_0;                      /* Two regular ranks, CH16 then CH17. */
    ADC1->SQR2  = 0U;
    ADC1->SQR3  = 16U | ( 17U << 5 );
    ADC1->CR2   = ADC_CR2_ADON | ADC_CR2_TSVREFE | ADC_CR2_EXTSEL | ADC_CR2_EXTTRIG | ADC_CR2_DMA;
    board_delay_ms( 2U ); /* Internal sources settle. DMA stays disabled during calibration. */
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
    /* F1 has no F0 ADSTART busy bit: enforce ownership of the DMA channel. */
    if ( ( DMA1_Channel1->CCR & DMA_CCR_EN ) != 0U )
    {
        board_adc_error = 6U;
        board_adc_fault();
    }
    if ( ( ADC1->CR2 & ADC_CR2_ADON ) == 0U )
    {
        board_adc_error = 3U;
        board_adc_fault();
    }
    const uint32_t before  = board_adc_sequences;
    DMA1->IFCR             = DMA_IFCR_CGIF1;
    DMA1_Channel1->CNDTR   = 2U;
    ADC1->SR               = 0U;
    DMA1_Channel1->CCR    |= DMA_CCR_EN;
    const uint32_t start   = board_ticks_ms;
    ADC1->CR2             |= ADC_CR2_SWSTART;
    while ( board_adc_sequences == before )
    {
        adc_deadline( start, 4U );
        __WFI();
    }
    board_adc_reading = adc_convert_f103( board_temperature_raw, board_reference_raw );
}
