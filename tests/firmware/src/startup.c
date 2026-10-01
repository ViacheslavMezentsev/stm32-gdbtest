/* Minimal Cortex-M startup: core vectors and profile-specific IRQs. */
#include <stdint.h>

extern uint32_t _estack, _sidata, _sdata, _edata, _sbss, _ebss;
extern int main( void );
#if defined( STM32F030x8 )
extern void SysTick_Handler( void );
extern void TIM3_IRQHandler( void );
extern void RTC_IRQHandler( void );
extern void DMA1_Channel1_IRQHandler( void );
#elif defined( STM32F103xB )
extern void SysTick_Handler( void );
extern void TIM2_IRQHandler( void );
extern void RTC_Alarm_IRQHandler( void );
extern void DMA1_Channel1_IRQHandler( void );
#elif defined( STM32F411xE )
extern void SysTick_Handler( void );
extern void TIM2_IRQHandler( void );
#endif

void Default_Handler( void )
{
    for ( ;; )
    {
    }
}

void HardFault_Handler( void )
{
    for ( ;; )
    {
    }
}
#if !defined( __ARM_ARCH_6M__ )
void MemManage_Handler( void )
{
    for ( ;; )
    {
    }
}

void BusFault_Handler( void )
{
    for ( ;; )
    {
    }
}

void UsageFault_Handler( void )
{
    for ( ;; )
    {
    }
}
#endif

void Reset_Handler( void )
{
    uint32_t* source = &_sidata;
    for ( uint32_t* dest = &_sdata; dest < &_edata; )
    {
        *dest++ = *source++;
    }
    for ( uint32_t* dest = &_sbss; dest < &_ebss; )
    {
        *dest++ = 0;
    }
    ( void ) main();
    for ( ;; )
    {
    }
}

// clang-format off
/* Core exceptions, followed by profile-specific external slots: SP, Reset, NMI, HardFault, MemManage, BusFault, UsageFault, reserved, SVC, DebugMon, reserved, PendSV, SysTick. */
__attribute__( ( section( ".isr_vector" ), used ) )
void ( *const vectors[] )( void ) = {
    ( void ( * )( void ) )( &_estack ), Reset_Handler, Default_Handler, HardFault_Handler,
#if defined( __ARM_ARCH_6M__ )
    0, 0, 0,
#else
    MemManage_Handler, BusFault_Handler, UsageFault_Handler,
#endif
    0, 0, 0, 0, Default_Handler, Default_Handler, 0, Default_Handler,
#if defined( STM32F030x8 )
    SysTick_Handler,
    /* STM32F030x8 external IRQ slots 0..15, then TIM3_IRQn=16. */
    Default_Handler, Default_Handler, RTC_IRQHandler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, DMA1_Channel1_IRQHandler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    TIM3_IRQHandler
#elif defined( STM32F103xB )
    SysTick_Handler,
    /* STM32F103xB external IRQ slots 0..27, then TIM2_IRQn=28. */
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, DMA1_Channel1_IRQHandler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    TIM2_IRQHandler,
    /* IRQ29..40, followed by RTC Alarm IRQ41. */
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    RTC_Alarm_IRQHandler
#elif defined( STM32F411xE )
    SysTick_Handler,
    /* F411 external IRQ0..27, followed by TIM2 IRQ28. */
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    TIM2_IRQHandler
#else
    Default_Handler
#endif
};
// clang-format on
