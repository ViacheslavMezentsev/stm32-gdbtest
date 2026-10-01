/* F411 scan CH18/17 and DMA2 stream0/channel0; no HAL or LL dependency. */
#include "app.h"
#include "adc_units.h"
#include "stm32f4xx.h"

/* DS10314: factory raw samples at VDDA=3.3 V, TS anchors 30/110 C. */
#define BOARD_VREF_CAL ( *( const uint16_t* ) 0x1FFF7A2AU )
#define BOARD_TS_CAL1  ( *( const uint16_t* ) 0x1FFF7A2CU )
#define BOARD_TS_CAL2  ( *( const uint16_t* ) 0x1FFF7A2EU )
#define STREAM_FLAGS   ( DMA_LIFCR_CFEIF0 | DMA_LIFCR_CDMEIF0 | DMA_LIFCR_CTEIF0 | DMA_LIFCR_CHTIF0 | DMA_LIFCR_CTCIF0 )

extern volatile uint32_t board_ticks_ms;
volatile uint16_t board_adc_buffer[2];
volatile uint16_t board_temperature_raw;
volatile uint16_t board_reference_raw;
volatile uint32_t board_adc_sequences;
volatile uint32_t board_adc_error;
volatile adc_reading_t board_adc_reading;

__attribute__( ( noreturn ) ) void board_adc_fault( void )
{
    ADC1->CR2        &= ~ADC_CR2_ADON;
    DMA2_Stream0->CR &= ~DMA_SxCR_EN;
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

void DMA2_Stream0_IRQHandler( void )
{
    const uint32_t flags = DMA2->LISR;
    if ( ( flags & ( DMA_LISR_TEIF0 | DMA_LISR_DMEIF0 | DMA_LISR_FEIF0 ) ) != 0U )
    {
        DMA2->LIFCR     = STREAM_FLAGS;
        board_adc_error = 5U;
        board_adc_fault();
    }
    if ( ( flags & DMA_LISR_TCIF0 ) != 0U )
    {
        /* Normal mode stops the stream after NDTR reaches zero. */
        DMA2->LIFCR           = STREAM_FLAGS;
        board_temperature_raw = board_adc_buffer[0];
        board_reference_raw   = board_adc_buffer[1];
        board_adc_sequences++;
    }
}

void board_adc_init( void )
{
    RCC->AHB1ENR |= RCC_AHB1ENR_DMA2EN;
    RCC->APB2ENR |= RCC_APB2ENR_ADC1EN;
    ( void ) RCC->APB2ENR;
    DMA2_Stream0->CR     &= ~DMA_SxCR_EN;
    const uint32_t start  = board_ticks_ms;
    while ( ( DMA2_Stream0->CR & DMA_SxCR_EN ) != 0U )
    {
        adc_deadline( start, 1U );
    }
    RCC->APB2RSTR |= RCC_APB2RSTR_ADCRST;
    RCC->APB2RSTR &= ~RCC_APB2RSTR_ADCRST;
    ADC->CCR       = ADC_CCR_TSVREFE; /* PCLK2/2=8 MHz, VBAT disabled, independent ADC. */
    ADC1->CR1      = ADC_CR1_SCAN;
    ADC1->SMPR1    = ADC_SMPR1_SMP18 | ADC_SMPR1_SMP17; /* 480 ADC cycles. */
    ADC1->SQR1     = ADC_SQR1_L_0;
    ADC1->SQR2     = 0U;
    ADC1->SQR3     = 18U | ( 17U << 5 );
    ADC1->CR2      = ADC_CR2_ADON | ADC_CR2_DMA | ADC_CR2_DDS;
    board_delay_ms( 2U ); /* ADC power-up and internal sensor settling. No F1 calibration. */
    DMA2_Stream0->CR   = DMA_SxCR_MINC | DMA_SxCR_PSIZE_0 | DMA_SxCR_MSIZE_0 | DMA_SxCR_TCIE | DMA_SxCR_TEIE | DMA_SxCR_DMEIE;
    DMA2_Stream0->FCR  = 0U; /* Direct mode. */
    DMA2_Stream0->PAR  = ( uint32_t ) &ADC1->DR;
    DMA2_Stream0->M0AR = ( uint32_t ) board_adc_buffer;
    DMA2->LIFCR        = STREAM_FLAGS;
    NVIC_ClearPendingIRQ( DMA2_Stream0_IRQn );
    NVIC_SetPriority( DMA2_Stream0_IRQn, 1U );
    NVIC_EnableIRQ( DMA2_Stream0_IRQn );
}

void board_adc_sample( void )
{
    /* DMA ownership guard, not an ADC conversion-busy indicator. */
    if ( ( DMA2_Stream0->CR & DMA_SxCR_EN ) != 0U )
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
    DMA2->LIFCR            = STREAM_FLAGS;
    DMA2_Stream0->NDTR     = 2U;
    ADC1->CR2             &= ~ADC_CR2_DMA;
    ADC1->SR               = 0U;
    ADC1->CR2             |= ADC_CR2_DMA;
    DMA2_Stream0->CR      |= DMA_SxCR_EN;
    const uint32_t start   = board_ticks_ms;
    ADC1->CR2             |= ADC_CR2_SWSTART;
    while ( board_adc_sequences == before )
    {
        adc_deadline( start, 4U );
        __WFI();
    }
    if ( ( ADC1->SR & ADC_SR_OVR ) != 0U )
    {
        board_adc_error = 7U;
        board_adc_fault();
    }
    board_adc_reading = adc_convert_f411( board_temperature_raw, board_reference_raw, BOARD_VREF_CAL, BOARD_TS_CAL1, BOARD_TS_CAL2 );
}
