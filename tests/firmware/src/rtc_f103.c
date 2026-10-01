/* F1 counter/alarm RTC: owns counter/prescaler, never resets the backup domain. */
#include "app.h"
#include "stm32f1xx.h"

extern volatile uint32_t board_ticks_ms;
volatile uint32_t board_rtc_events;
volatile uint32_t board_rtc_error;
static volatile uint32_t rtc_rearm_pending;

__attribute__( ( noreturn ) ) void board_rtc_fault( void )
{
    NVIC_DisableIRQ( RTC_Alarm_IRQn );
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
    rtc_wait( &RTC->CRL, RTC_CRL_RTOFF, 5U );
    RTC->CRL = RTC_CRL_RSF | RTC_CRL_OWF | RTC_CRL_ALRF | RTC_CRL_SECF | RTC_CRL_CNF;
}

static void rtc_end_write( void )
{
    RTC->CRL = RTC_CRL_RSF | RTC_CRL_OWF | RTC_CRL_ALRF | RTC_CRL_SECF;
    rtc_wait( &RTC->CRL, RTC_CRL_RTOFF, 6U );
}

void RTC_Alarm_IRQHandler( void )
{
    if ( ( RTC->CRL & RTC_CRL_ALRF ) != 0U )
    {
        /* rc_w0 flags: preserve other flags; CNF must stay clear. */
        RTC->CRL = RTC_CRL_RSF | RTC_CRL_OWF | RTC_CRL_SECF;
        EXTI->PR = EXTI_PR_PR17;
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
            high = RTC->CNTH;
            low  = RTC->CNTL;
        } while ( high != RTC->CNTH );
        const uint32_t alarm = ( ( high << 16 ) | low ) + 2U;
        rtc_rearm_pending    = 0U;
        /* All bounded waits run in thread mode, where SysTick can advance. */
        rtc_begin_write();
        RTC->ALRH = alarm >> 16;
        RTC->ALRL = alarm & 0xFFFFU;
        rtc_end_write();
    }
}

void board_rtc_init( void )
{
    RCC->APB1ENR |= RCC_APB1ENR_PWREN | RCC_APB1ENR_BKPEN;
    ( void ) RCC->APB1ENR;
    PWR->CR |= PWR_CR_DBP;
    rtc_wait( &PWR->CR, PWR_CR_DBP, 1U );
    const uint32_t source = RCC->BDCR & RCC_BDCR_RTCSEL;
    if ( source != 0U && source != RCC_BDCR_RTCSEL_LSI )
    {
        board_rtc_error = 2U;
        board_rtc_fault();
    }
    RCC->CSR |= RCC_CSR_LSION;
    rtc_wait( &RCC->CSR, RCC_CSR_LSIRDY, 3U );
    RCC->BDCR |= RCC_BDCR_RTCSEL_LSI | RCC_BDCR_RTCEN;
    NVIC_DisableIRQ( RTC_IRQn );
    NVIC_DisableIRQ( RTC_Alarm_IRQn );
    RTC->CRL = RTC_CRL_OWF | RTC_CRL_ALRF | RTC_CRL_SECF;
    rtc_wait( &RTC->CRL, RTC_CRL_RSF, 4U );
    rtc_begin_write();
    RTC->CRH  = 0U;
    RTC->PRLH = 0U;
    RTC->PRLL = 39999U; /* Nominal LSI 40 kHz, not a precision reference. */
    RTC->CNTH = 0U;
    RTC->CNTL = 0U;
    RTC->ALRH = 0U;
    RTC->ALRL = 2U;
    rtc_end_write();
    RTC->CRL    = RTC_CRL_RSF; /* Clear pending flags, keep synchronization. */
    EXTI->FTSR &= ~EXTI_FTSR_TR17;
    EXTI->RTSR |= EXTI_RTSR_TR17;
    EXTI->PR    = EXTI_PR_PR17;
    EXTI->IMR  |= EXTI_IMR_MR17;
    NVIC_ClearPendingIRQ( RTC_Alarm_IRQn );
    NVIC_SetPriority( RTC_Alarm_IRQn, 2U );
    RTC->CRH = RTC_CRH_ALRIE;
    rtc_wait( &RTC->CRL, RTC_CRL_RTOFF, 6U );
    NVIC_EnableIRQ( RTC_Alarm_IRQn );
}
