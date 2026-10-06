/* AT32F403A counter/alarm RTC (F1-compatible layout): owns counter/divider, never resets the battery domain. */
#include "app.h"
#include "at32f403a_407.h"
#include "at32_bits.h"

extern volatile uint32_t board_ticks_ms;
volatile uint32_t board_rtc_events;
volatile uint32_t board_rtc_error;
static volatile uint32_t rtc_rearm_pending;

__attribute__( ( noreturn ) ) void board_rtc_fault( void )
{
    NVIC_DisableIRQ( RTCAlarm_IRQn );
    for ( ;; )
    {
        __WFI();
    }
}

static void rtc_wait( volatile uint32_t* reg, uint32_t mask, uint32_t error )
{
    const uint32_t start = board_ticks_ms;
    while ( ( *reg & mask ) == 0U )
    {
        if ( ( uint32_t ) ( board_ticks_ms - start ) >= 1000U )
        {
            board_rtc_error = error;
            board_rtc_fault();
        }
    }
}

static void rtc_begin_write( void )
{
    rtc_wait( &RTC->ctrll, AT32_RTC_CTRLL_CFGF, 5U );
    RTC->ctrll = AT32_RTC_CTRLL_UPDF | AT32_RTC_CTRLL_OVFF | AT32_RTC_CTRLL_TAF | AT32_RTC_CTRLL_TSF | AT32_RTC_CTRLL_CFGEN;
}

static void rtc_end_write( void )
{
    RTC->ctrll = AT32_RTC_CTRLL_UPDF | AT32_RTC_CTRLL_OVFF | AT32_RTC_CTRLL_TAF | AT32_RTC_CTRLL_TSF;
    rtc_wait( &RTC->ctrll, AT32_RTC_CTRLL_CFGF, 6U );
}

void RTC_Alarm_IRQHandler( void )
{
    if ( ( RTC->ctrll & AT32_RTC_CTRLL_TAF ) != 0U )
    {
        /* Write-0-to-clear flags: preserve the others; CFGEN must stay clear. */
        RTC->ctrll    = AT32_RTC_CTRLL_UPDF | AT32_RTC_CTRLL_OVFF | AT32_RTC_CTRLL_TSF;
        EXINT->intsts = AT32_EXINT_LINE17;
        board_rtc_events++;
        rtc_rearm_pending = 1U;
    }
}

void board_rtc_service( void )
{
    if ( rtc_rearm_pending != 0U )
    {
        uint32_t high, low;
        do
        {
            high = RTC->cnth;
            low  = RTC->cntl;
        } while ( high != RTC->cnth );
        const uint32_t alarm = ( ( high << 16 ) | low ) + 2U;
        rtc_rearm_pending    = 0U;
        /* All bounded waits run in thread mode, where SysTick can advance. */
        rtc_begin_write();
        RTC->tah = alarm >> 16;
        RTC->tal = alarm & 0xFFFFU;
        rtc_end_write();
    }
}

void board_rtc_init( void )
{
    CRM->apb1en |= AT32_CRM_APB1_PWC | AT32_CRM_APB1_BPR;
    ( void ) CRM->apb1en;
    PWC->ctrl |= AT32_PWC_CTRL_BPWEN;
    rtc_wait( &PWC->ctrl, AT32_PWC_CTRL_BPWEN, 1U );
    const uint32_t source = CRM->bpdc & AT32_CRM_BPDC_RTCSEL;
    if ( source != 0U && source != AT32_CRM_BPDC_RTCSEL_LICK )
    {
        board_rtc_error = 2U;
        board_rtc_fault();
    }
    CRM->ctrlsts |= AT32_CRM_CTRLSTS_LICKEN;
    rtc_wait( &CRM->ctrlsts, AT32_CRM_CTRLSTS_LICKSTBL, 3U );
    CRM->bpdc |= AT32_CRM_BPDC_RTCSEL_LICK | AT32_CRM_BPDC_RTCEN;
    NVIC_DisableIRQ( RTC_IRQn );
    NVIC_DisableIRQ( RTCAlarm_IRQn );
    RTC->ctrll = AT32_RTC_CTRLL_OVFF | AT32_RTC_CTRLL_TAF | AT32_RTC_CTRLL_TSF;
    rtc_wait( &RTC->ctrll, AT32_RTC_CTRLL_UPDF, 4U );
    rtc_begin_write();
    RTC->ctrlh = 0U;
    RTC->divh  = 0U;
    RTC->divl  = 39999U; /* Nominal LICK 40 kHz, not a precision reference. */
    RTC->cnth  = 0U;
    RTC->cntl  = 0U;
    RTC->tah   = 0U;
    RTC->tal   = 2U;
    rtc_end_write();
    RTC->ctrll      = AT32_RTC_CTRLL_UPDF; /* Clear pending flags, keep synchronization. */
    EXINT->polcfg2 &= ~AT32_EXINT_LINE17;
    EXINT->polcfg1 |= AT32_EXINT_LINE17;
    EXINT->intsts   = AT32_EXINT_LINE17;
    EXINT->inten   |= AT32_EXINT_LINE17;
    NVIC_ClearPendingIRQ( RTCAlarm_IRQn );
    NVIC_SetPriority( RTCAlarm_IRQn, 2U );
    RTC->ctrlh = AT32_RTC_CTRLH_TAIEN;
    rtc_wait( &RTC->ctrll, AT32_RTC_CTRLL_CFGF, 6U );
    NVIC_EnableIRQ( RTCAlarm_IRQn );
}
