/* F411 calendar/alarm example; owns the RTC calendar, but never resets backup domain. */
#include "app.h"
#include "stm32f4xx.h"

extern volatile uint32_t board_ticks_ms;
volatile uint32_t board_rtc_events;
volatile uint32_t board_rtc_error;

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

void RTC_Alarm_IRQHandler( void )
{
    if ( ( RTC->ISR & RTC_ISR_ALRAF ) != 0U )
    {
        /* rc_w0 flag, keep INIT clear and preserve other pending flags. */
        RTC->ISR = ~( RTC_ISR_ALRAF | RTC_ISR_INIT );
        EXTI->PR = EXTI_PR_PR17; /* W1C, not read-modify-write. */
        board_rtc_events++;
    }
}

void board_rtc_init( void )
{
    RCC->APB1ENR |= RCC_APB1ENR_PWREN;
    ( void ) RCC->APB1ENR;
    PWR->CR |= PWR_CR_DBP;
    rtc_wait( &PWR->CR, PWR_CR_DBP, 1U );
    const uint32_t source = RCC->BDCR & RCC_BDCR_RTCSEL;
    if ( source != 0U && source != RCC_BDCR_RTCSEL_1 )
    {
        /* Changing an existing clock source needs BDRST: refuse instead. */
        board_rtc_error = 2U;
        board_rtc_fault();
    }
    RCC->CSR |= RCC_CSR_LSION;
    rtc_wait( &RCC->CSR, RCC_CSR_LSIRDY, 3U );
    RCC->BDCR |= RCC_BDCR_RTCSEL_1 | RCC_BDCR_RTCEN;
    NVIC_DisableIRQ( RTC_Alarm_IRQn );
    RTC->WPR = 0xCAU;
    RTC->WPR = 0x53U;
    RTC->CR  = 0U;
    rtc_wait( &RTC->ISR, RTC_ISR_ALRAWF, 4U );
    RTC->ISR = RTC_ISR_INIT;
    rtc_wait( &RTC->ISR, RTC_ISR_INITF, 5U );
    /* Nominal LSI 32 kHz / 128 / 250; this is not a precision timebase. */
    RTC->PRER     = ( 127U << 16 ) | 249U;
    RTC->TR       = 0U;
    RTC->DR       = 0x002101U; /* Monday, January 1, year 00: fixture epoch. */
    RTC->ALRMAR   = RTC_ALRMAR_MSK1 | RTC_ALRMAR_MSK2 | RTC_ALRMAR_MSK3 | RTC_ALRMAR_MSK4;
    RTC->ALRMASSR = 0U; /* All subseconds masked: alarm every calendar second. */
    RTC->ISR      = 0U; /* Exit INIT, clear flags and RSF. */
    rtc_wait( &RTC->ISR, RTC_ISR_RSF, 6U );
    EXTI->FTSR &= ~EXTI_FTSR_TR17;
    EXTI->RTSR |= EXTI_RTSR_TR17;
    EXTI->PR    = EXTI_PR_PR17;
    EXTI->IMR  |= EXTI_IMR_MR17;
    NVIC_ClearPendingIRQ( RTC_Alarm_IRQn );
    NVIC_SetPriority( RTC_Alarm_IRQn, 2U );
    RTC->CR  = RTC_CR_ALRAIE | RTC_CR_ALRAE;
    RTC->WPR = 0xFFU;
    NVIC_EnableIRQ( RTC_Alarm_IRQn );
}
