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

// Neutral fixtures for the memory/write API contract; no peripheral model.
volatile unsigned rhs_calls;
volatile unsigned receiver;
unsigned long long wide_value;
signed char small_signed;
unsigned char small_unsigned;
float float_value;
bool bool_value;
Counter* counter_pointer;

enum Mode
{
    MODE_IDLE,
    MODE_RUN
};

Mode mode_value;

extern "C" __attribute__( ( noinline ) ) unsigned next_value()
{
    return ++rhs_calls;
}

extern "C" __attribute__( ( noinline ) ) unsigned constant_value()
{
    ++rhs_calls;
    return 42;
}
