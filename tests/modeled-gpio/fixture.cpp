typedef unsigned int u32;

// Публикуем результат штатного чтения периферии, а не запись самого сценария.
struct Observation
{
    u32 raw, active, neighbour, samples;
};

volatile Observation observation;

extern "C" void ready()
{
    asm volatile( "nop" );
}

extern "C" void sampled()
{
    asm volatile( "nop" );
}

// Один обработчик на host и MCU; источник чтения на MCU остаётся volatile MMIO.
static void consume( u32 pins )
{
    observation.raw       = pins;
    observation.active    = pins & 1;
    observation.neighbour = ( pins >> 1 ) & 1;
    ++observation.samples;
}

#ifdef HOST
#include <cassert>

int main()
{
    const u32 levels[] = { 2, 3, 3, 2, 3, 2 };
    for ( u32 i = 0; i < 6; ++i )
    {
        consume( levels[i] );
        assert( observation.raw == levels[i] );
        assert( observation.active == ( levels[i] & 1 ) );
        assert( observation.neighbour == 1 );
        assert( observation.samples == i + 1 );
    }
}
#else
extern "C" void Reset_Handler()
{
    observation.raw = observation.active = observation.neighbour = observation.samples = 0;
    while ( true )
    {
        ready();
        consume( *( volatile u32* ) 0x40000000 );
        sampled();
    }
}

__attribute__( ( section( ".vectors" ), used ) ) const unsigned vectors[] = { 0x20010000, ( unsigned ) &Reset_Handler };
#endif
