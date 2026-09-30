/* Minimal Cortex-M startup: core vectors only, no peripheral IRQ. */
#include <stdint.h>

extern uint32_t _estack, _sidata, _sdata, _edata, _sbss, _ebss;
extern int main( void );

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
/* Core exceptions only: SP, Reset, NMI, HardFault, MemManage, BusFault, UsageFault, reserved, SVC, DebugMon, reserved, PendSV, SysTick. */
__attribute__( ( section( ".isr_vector" ), used ) )
void ( *const vectors[] )( void ) = {
    ( void ( * )( void ) )( &_estack ), Reset_Handler, Default_Handler, HardFault_Handler,
#if defined( __ARM_ARCH_6M__ )
    0, 0, 0,
#else
    MemManage_Handler, BusFault_Handler, UsageFault_Handler,
#endif
    0, 0, 0, 0, Default_Handler, Default_Handler, 0, Default_Handler, Default_Handler
};
// clang-format on
