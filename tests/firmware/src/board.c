/* Board LED through CMSIS registers only; the family is selected by the device define. */
#include "app.h"

#if defined( STM32F030x8 )
#include "stm32f0xx.h"

/* NUCLEO-F030R8: LD2 on PA5. */
uint32_t SystemCoreClock = 8000000U;
volatile uint32_t board_ticks_ms;
volatile uint32_t board_timer_events;

void TIM3_IRQHandler( void )
{
    if ( ( TIM3->SR & TIM_SR_UIF ) != 0U )
    {
        /* UIF is cleared by writing zero, without an SR read-modify-write. */
        TIM3->SR = ~TIM_SR_UIF;
        board_timer_events++;
    }
}

static void board_timer_init( void )
{
    RCC->APB1ENR |= RCC_APB1ENR_TIM3EN;
    ( void ) RCC->APB1ENR;
    RCC->APB1RSTR |= RCC_APB1RSTR_TIM3RST;
    RCC->APB1RSTR &= ~RCC_APB1RSTR_TIM3RST;
    TIM3->PSC      = 7999U;
    TIM3->ARR      = 99U;
    TIM3->EGR      = TIM_EGR_UG;
    /* UG loads the prescaler and sets UIF: discard this initialization event. */
    TIM3->SR = 0U;
    NVIC_ClearPendingIRQ( TIM3_IRQn );
    NVIC_SetPriority( TIM3_IRQn, 2U );
    TIM3->DIER = TIM_DIER_UIE;
    NVIC_EnableIRQ( TIM3_IRQn );
    TIM3->CR1 = TIM_CR1_CEN;
}

void SysTick_Handler( void )
{
    board_ticks_ms++;
}

void board_delay_ms( uint32_t delay_ms )
{
    const uint32_t start = board_ticks_ms;
    while ( ( uint32_t ) ( board_ticks_ms - start ) < delay_ms )
    {
        __WFI();
    }
}

void board_init( void )
{
    RCC->CR |= RCC_CR_HSION;
    while ( ( RCC->CR & RCC_CR_HSIRDY ) == 0U )
    {
    }
    RCC->CFGR &= ~( RCC_CFGR_SW | RCC_CFGR_HPRE | RCC_CFGR_PPRE );
    while ( ( RCC->CFGR & RCC_CFGR_SWS ) != RCC_CFGR_SWS_HSI )
    {
    }
    RCC->CR         &= ~RCC_CR_PLLON;
    SystemCoreClock  = 8000000U;
    RCC->AHBENR     |= RCC_AHBENR_GPIOAEN;
    ( void ) RCC->AHBENR;
    GPIOA->BSRR     = GPIO_BSRR_BR_5;
    GPIOA->OTYPER  &= ~GPIO_OTYPER_OT_5;
    GPIOA->OSPEEDR &= ~GPIO_OSPEEDR_OSPEEDR5;
    GPIOA->PUPDR   &= ~GPIO_PUPDR_PUPDR5;
    GPIOA->MODER    = ( GPIOA->MODER & ~GPIO_MODER_MODER5 ) | GPIO_MODER_MODER5_0;
    /* Constant division keeps this Cortex-M0 fixture independent of libgcc division. */
    ( void ) SysTick_Config( 8000000U / 1000U );
    board_timer_init();
    board_adc_init();
    board_rtc_init();
}

void board_led_toggle( void )
{
    GPIOA->ODR ^= GPIO_ODR_5;
}
#elif defined( STM32F103xB )
#include "stm32f1xx.h"

/* WeAct BluePill-Plus: PB2, active-high LED, push-pull output 2 MHz. */
uint32_t SystemCoreClock = 8000000U;
volatile uint32_t board_ticks_ms;
volatile uint32_t board_timer_events;

void SysTick_Handler( void )
{
    board_ticks_ms++;
}

void TIM2_IRQHandler( void )
{
    if ( ( TIM2->SR & TIM_SR_UIF ) != 0U )
    {
        TIM2->SR = ~TIM_SR_UIF;
        board_timer_events++;
    }
}

void board_delay_ms( uint32_t delay_ms )
{
    const uint32_t start = board_ticks_ms;
    while ( ( uint32_t ) ( board_ticks_ms - start ) < delay_ms )
    {
        __WFI();
    }
}

static void board_timer_init( void )
{
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    ( void ) RCC->APB1ENR;
    RCC->APB1RSTR |= RCC_APB1RSTR_TIM2RST;
    RCC->APB1RSTR &= ~RCC_APB1RSTR_TIM2RST;
    TIM2->PSC      = 7999U;
    TIM2->ARR      = 99U;
    TIM2->EGR      = TIM_EGR_UG;
    /* Discard the update flag from loading the prescaler. */
    TIM2->SR = 0U;
    NVIC_ClearPendingIRQ( TIM2_IRQn );
    NVIC_SetPriority( TIM2_IRQn, 2U );
    TIM2->DIER = TIM_DIER_UIE;
    NVIC_EnableIRQ( TIM2_IRQn );
    TIM2->CR1 = TIM_CR1_CEN;
}

void board_init( void )
{
    RCC->CR |= RCC_CR_HSION;
    while ( ( RCC->CR & RCC_CR_HSIRDY ) == 0U )
    {
    }
    RCC->CFGR &= ~( RCC_CFGR_SW | RCC_CFGR_HPRE | RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2 );
    while ( ( RCC->CFGR & RCC_CFGR_SWS ) != RCC_CFGR_SWS_HSI )
    {
    }
    RCC->CR         &= ~RCC_CR_PLLON;
    SystemCoreClock  = 8000000U;
    RCC->APB2ENR    |= RCC_APB2ENR_IOPBEN;
    ( void ) RCC->APB2ENR;
    GPIOB->BSRR = GPIO_BSRR_BR2;
    GPIOB->CRL  = ( GPIOB->CRL & ~( GPIO_CRL_MODE2 | GPIO_CRL_CNF2 ) ) | GPIO_CRL_MODE2_1;
    ( void ) SysTick_Config( 8000000U / 1000U );
    board_timer_init();
    board_adc_init();
    board_rtc_init();
}

void board_led_toggle( void )
{
    GPIOB->ODR ^= GPIO_ODR_ODR2;
}
#elif defined( STM32F411xE )
#include "stm32f4xx.h"

/* WeAct BlackPill F411: PC13, active-low LED; HSI nominal 16 MHz. */
uint32_t SystemCoreClock = 16000000U;
volatile uint32_t board_ticks_ms;
volatile uint32_t board_timer_events;

void SysTick_Handler( void )
{
    board_ticks_ms++;
}

void TIM2_IRQHandler( void )
{
    if ( ( TIM2->SR & TIM_SR_UIF ) != 0U )
    {
        TIM2->SR = ~TIM_SR_UIF;
        board_timer_events++;
    }
}

void board_delay_ms( uint32_t delay_ms )
{
    const uint32_t start = board_ticks_ms;
    while ( ( uint32_t ) ( board_ticks_ms - start ) < delay_ms )
    {
        __WFI();
    }
}

static void board_timer_init( void )
{
    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    ( void ) RCC->APB1ENR;
    RCC->APB1RSTR |= RCC_APB1RSTR_TIM2RST;
    RCC->APB1RSTR &= ~RCC_APB1RSTR_TIM2RST;
    TIM2->PSC      = 15999U;
    TIM2->ARR      = 99U;
    TIM2->EGR      = TIM_EGR_UG;
    /* Discard the update flag from loading the prescaler. */
    TIM2->SR = 0U;
    NVIC_ClearPendingIRQ( TIM2_IRQn );
    NVIC_SetPriority( TIM2_IRQn, 2U );
    TIM2->DIER = TIM_DIER_UIE;
    NVIC_EnableIRQ( TIM2_IRQn );
    TIM2->CR1 = TIM_CR1_CEN;
}

void board_init( void )
{
    RCC->CR |= RCC_CR_HSION;
    while ( ( RCC->CR & RCC_CR_HSIRDY ) == 0U )
    {
    }
    RCC->CFGR &= ~( RCC_CFGR_SW | RCC_CFGR_HPRE | RCC_CFGR_PPRE1 | RCC_CFGR_PPRE2 );
    while ( ( RCC->CFGR & RCC_CFGR_SWS ) != RCC_CFGR_SWS_HSI )
    {
    }
    RCC->CR         &= ~RCC_CR_PLLON;
    SystemCoreClock  = 16000000U;
    RCC->AHB1ENR    |= RCC_AHB1ENR_GPIOCEN;
    ( void ) RCC->AHB1ENR;
    GPIOC->BSRR     = GPIO_BSRR_BS13;
    GPIOC->OTYPER  &= ~GPIO_OTYPER_OT13;
    GPIOC->OSPEEDR &= ~GPIO_OSPEEDER_OSPEEDR13;
    GPIOC->PUPDR   &= ~GPIO_PUPDR_PUPD13;
    GPIOC->MODER    = ( GPIOC->MODER & ~GPIO_MODER_MODER13 ) | GPIO_MODER_MODER13_0;
    ( void ) SysTick_Config( 16000000U / 1000U );
    board_timer_init();
    board_adc_init();
    board_rtc_init();
}

void board_led_toggle( void )
{
    GPIOC->ODR ^= GPIO_ODR_OD13;
}
#else
#error "Unsupported CI device"
#endif
