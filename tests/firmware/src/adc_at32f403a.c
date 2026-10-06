/* AT32F403A internal temperature/VINTRV: ordinary scan and normal DMA (F1-compatible layout), no SDK drivers. */
#include "app.h"
#include "adc_units.h"
#include "at32f403a_407.h"
#include "at32_bits.h"

extern volatile uint32_t board_ticks_ms;
volatile uint16_t board_adc_buffer[2];
volatile uint16_t board_temperature_raw;
volatile uint16_t board_reference_raw;
volatile uint32_t board_adc_sequences;
volatile uint32_t board_adc_error;
volatile adc_reading_t board_adc_reading;

__attribute__( ( noreturn ) ) void board_adc_fault( void )
{
    DMA1_CHANNEL1->ctrl &= ~AT32_DMA_CTRL_CHEN;
    ADC1->ctrl2         &= ~AT32_ADC_CTRL2_ADCEN;
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
    const uint32_t flags = DMA1->sts;
    if ( ( flags & AT32_DMA_STS_DTERRF1 ) != 0U )
    {
        DMA1->clr       = AT32_DMA_CLR_GFC1;
        board_adc_error = 5U;
        board_adc_fault();
    }
    if ( ( flags & AT32_DMA_STS_FDTF1 ) != 0U )
    {
        DMA1_CHANNEL1->ctrl   &= ~AT32_DMA_CTRL_CHEN;
        DMA1->clr              = AT32_DMA_CLR_GFC1;
        board_temperature_raw  = board_adc_buffer[0];
        board_reference_raw    = board_adc_buffer[1];
        board_adc_sequences++;
    }
}

void board_adc_init( void )
{
    CRM->ahben  |= AT32_CRM_AHB_DMA1;
    CRM->apb2en |= AT32_CRM_APB2_ADC1;
    ( void ) CRM->apb2en;
    CRM->apb2rst |= AT32_CRM_APB2_ADC1;
    CRM->apb2rst &= ~AT32_CRM_APB2_ADC1;
    CRM->cfg     &= ~AT32_CRM_CFG_ADCDIV; /* PCLK2 / 2 = 4 MHz, below the 28 MHz limit. */
    ADC1->ctrl1   = AT32_ADC_CTRL1_SQEN;
    ADC1->ctrl2   = AT32_ADC_CTRL2_ADCEN;
    board_delay_ms( 2U ); /* Power-up (tSTAB) before the calibration reset. */
    ADC1->ctrl2    |= AT32_ADC_CTRL2_ADCALINIT;
    uint32_t start  = board_ticks_ms;
    while ( ( ADC1->ctrl2 & AT32_ADC_CTRL2_ADCALINIT ) != 0U )
    {
        adc_deadline( start, 1U );
    }
    ADC1->ctrl2 |= AT32_ADC_CTRL2_ADCAL;
    start        = board_ticks_ms;
    while ( ( ADC1->ctrl2 & AT32_ADC_CTRL2_ADCAL ) != 0U )
    {
        adc_deadline( start, 2U );
    }
    ADC1->spt1  = AT32_ADC_SPT1_CSPT16_MAX | AT32_ADC_SPT1_CSPT17_MAX; /* 239.5 ADC cycles. */
    ADC1->osq1  = AT32_ADC_OSQ1_OCLEN_2;                               /* Two ordinary ranks, IN16 then IN17. */
    ADC1->osq2  = 0U;
    ADC1->osq3  = 16U | ( 17U << 5 );
    ADC1->ctrl2 = AT32_ADC_CTRL2_ADCEN | AT32_ADC_CTRL2_ITSRVEN | AT32_ADC_CTRL2_OCTESEL_SW | AT32_ADC_CTRL2_OCTEN | AT32_ADC_CTRL2_OCDMAEN;
    board_delay_ms( 2U ); /* Internal sources settle. DMA stays disabled during calibration. */
    DMA1_CHANNEL1->ctrl =
        AT32_DMA_CTRL_MINCM | AT32_DMA_CTRL_PWIDTH_16 | AT32_DMA_CTRL_MWIDTH_16 | AT32_DMA_CTRL_FDTIEN | AT32_DMA_CTRL_DTERRIEN;
    DMA1_CHANNEL1->paddr = ( uint32_t ) &ADC1->odt;
    DMA1_CHANNEL1->maddr = ( uint32_t ) board_adc_buffer;
    DMA1->clr            = AT32_DMA_CLR_GFC1;
    NVIC_ClearPendingIRQ( DMA1_Channel1_IRQn );
    NVIC_SetPriority( DMA1_Channel1_IRQn, 1U );
    NVIC_EnableIRQ( DMA1_Channel1_IRQn );
}

void board_adc_sample( void )
{
    /* As on F1 there is no busy bit: enforce ownership of the DMA channel. */
    if ( ( DMA1_CHANNEL1->ctrl & AT32_DMA_CTRL_CHEN ) != 0U )
    {
        board_adc_error = 6U;
        board_adc_fault();
    }
    if ( ( ADC1->ctrl2 & AT32_ADC_CTRL2_ADCEN ) == 0U )
    {
        board_adc_error = 3U;
        board_adc_fault();
    }
    const uint32_t before  = board_adc_sequences;
    DMA1->clr              = AT32_DMA_CLR_GFC1;
    DMA1_CHANNEL1->dtcnt   = 2U;
    ADC1->sts              = 0U;
    DMA1_CHANNEL1->ctrl   |= AT32_DMA_CTRL_CHEN;
    const uint32_t start   = board_ticks_ms;
    ADC1->ctrl2           |= AT32_ADC_CTRL2_OCSWTRG;
    while ( board_adc_sequences == before )
    {
        adc_deadline( start, 4U );
        __WFI();
    }
    board_adc_reading = adc_convert_at32f403a( board_temperature_raw, board_reference_raw );
}
