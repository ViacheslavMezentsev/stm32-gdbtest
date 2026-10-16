// Neutral C++ fixture: explicit startup, no peripherals or runtime library.
struct Probe
{
    unsigned value;
    __attribute__( ( noinline ) ) void add( unsigned n );
    __attribute__( ( noinline ) ) unsigned read() const;
    __attribute__( ( noinline ) ) static unsigned twice( unsigned n );

    __attribute__( ( always_inline ) ) inline unsigned absent() const { return value; }
};

void Probe::add( unsigned n )
{
    value += n;
}

unsigned Probe::read() const
{
    return value;
}

unsigned Probe::twice( unsigned n )
{
    return 2 * n;
}

namespace demo
{
    __attribute__( ( noinline ) ) unsigned increment( unsigned n )
    {
        return n + 1;
    }
}

Probe probe;

extern "C" __attribute__( ( noinline ) ) void ready()
{
    asm volatile( "nop" );
}

__attribute__( ( noinline ) ) unsigned free_cpp( unsigned n )
{
    return n + 2;
}

extern "C" __attribute__( ( noinline ) ) void set_value( unsigned n )
{
    probe.value = n;
}

extern "C" void Reset_Handler()
{
    probe.value = 3;
    ready();
    while ( true )
    {
        asm volatile( "nop" );
    }
}

__attribute__( ( section( ".vectors" ), used ) ) const unsigned vectors[] = { 0x20010000, ( unsigned ) &Reset_Handler };
