#include <stdint.h>
/* This neutral workload owns the IRQ and linker-reserved observer SRAM. */
#define REG( a ) ( *( volatile uint32_t* ) ( a ) )
volatile uint32_t requested, delivered, calls, checksum, rounds, release;
typedef uint32_t ( *work_t )( uint32_t );
volatile work_t work;

__attribute__( ( noinline ) ) void ready( void )
{
    __asm volatile( "nop" );
}

__attribute__( ( noinline ) ) void finished( void )
{
    __asm volatile( "nop" );
}

__attribute__( ( noinline, aligned( 4 ) ) ) uint32_t original_work( uint32_t x )
{
    calls++;
    return x * 3 + 1;
}

void original_irq( void )
{
    delivered++;
}

void fault( void )
{
    for ( ;; )
        __asm volatile( "nop" );
}

void main( void )
{
    requested = delivered = calls = checksum = rounds = release = 0;
    work                                                        = original_work;
    REG( 0xE000ED08 )                                           = 0x08000000;
    __asm volatile( "cpsie i" );
    for ( ;; )
    {
        ready();
        uint32_t n = requested;
        for ( uint32_t i = 0; i < n; ++i )
        {
            checksum        += work( i );
            uint32_t before  = delivered;

            /* Pending bits are not a queue: acknowledge each IRQ before the next one. */
            REG( 0xE000E200 ) = 1;
            __asm volatile( "dsb\nisb" ::: "memory" );
            while ( delivered == before )
                __asm volatile( "nop" );
        }
        rounds++;
        finished();
        while ( !release )
            __asm volatile( "nop" );
        release = 0;
    }
}

void Reset_Handler( void )
{
    __asm volatile( "cpsid i" );
    REG( 0xE000E010 ) = 0;
    for ( unsigned i = 0; i < 8; ++i )
    {
        REG( 0xE000E180 + 4 * i ) = 0xffffffff;
        REG( 0xE000E280 + 4 * i ) = 0xffffffff;
    }
    __asm volatile( "movs r0,#0\nmsr basepri,r0\nmsr faultmask,r0" ::: "r0", "memory" );
    main();
    for ( ;; )
    {
    }
}

__attribute__( ( section( ".vectors" ), used ) ) const uintptr_t vectors[128] = { [0 ... 127] = ( uintptr_t ) fault,
    [0]                                                                                       = 0x20007000,
    [1]                                                                                       = ( uintptr_t ) Reset_Handler,
    [2]                                                                                       = ( uintptr_t ) fault,
    [3]                                                                                       = ( uintptr_t ) fault,
    [16]                                                                                      = ( uintptr_t ) original_irq };
