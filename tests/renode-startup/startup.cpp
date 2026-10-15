// Neutral startup and C++ state; no hardware peripheral claims.
struct Counter
{
    unsigned value;

    void add( unsigned n ) { value += n; }
};

Counter counter;
volatile unsigned started;

extern "C" void ready()
{
    asm volatile( "nop" );
}

extern "C" void Reset_Handler()
{
    counter.value = 0;
    started       = 1;
    counter.add( 3 );
    ready();
    while ( true )
    {
        asm volatile( "nop" );
    }
}

__attribute__( ( section( ".vectors" ), used ) ) const unsigned vectors[] = { 0x20010000, ( unsigned ) &Reset_Handler };
