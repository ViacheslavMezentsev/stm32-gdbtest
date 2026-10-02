#include "abi_values.h"

volatile double accepted_double;
volatile float accepted_float;
volatile uint32_t accepted_stack;
volatile uint32_t abi_cycles;

void process_abi( void )
{
    accumulate( 3 );
    accepted_double = affine( 2.5, 0.5 );
    accepted_float  = gain_adjust( 3.5f );
    accepted_stack  = weighted_sum( 1, 2, 3, 4, 5, 6 );
}

int main( void )
{
#if defined( __ARM_PCS_VFP )
    /* Enable CP10/CP11 before calling any floating-point code on Cortex-M4F. */
    *( volatile uint32_t* ) 0xe000ed88 |= 0x00f00000;
    __asm volatile( "dsb\nisb" ::: "memory" );
#endif
    for ( ;; )
    {
        process_abi();
        abi_cycles++;
    }
}
