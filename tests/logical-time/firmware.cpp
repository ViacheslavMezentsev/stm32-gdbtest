#include "model.hpp"

extern "C" __attribute__( ( noinline ) ) void ready()
{
    asm volatile( "nop" );
}

extern "C" int main()
{
    model_reset();
    ready();
    while ( true )
        asm volatile( "nop" );
}

extern "C" void Reset_Handler()
{
    main();
}

__attribute__( ( section( ".vectors" ), used ) ) const unsigned vectors[] = { 0x20010000, ( unsigned ) &Reset_Handler };
