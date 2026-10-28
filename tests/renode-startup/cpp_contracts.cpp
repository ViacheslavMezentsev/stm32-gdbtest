volatile unsigned calls;
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
    ++calls;
    return 2 * n;
}

namespace demo
{
    __attribute__( ( noinline ) ) unsigned increment( unsigned n )
    {
        ++calls;
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
    ++calls;
    return n + 2;
}

extern "C" __attribute__( ( noinline ) ) void set_value( unsigned n )
{
    probe.value = n;
}

extern "C" void main()
{
    calls = 0;
    probe.value = 3;
    ready();
    while ( true )
    {
        asm volatile( "nop" );
    }
}

extern "C" void Reset_Handler() { main(); }

__attribute__( ( section( ".vectors" ), used ) ) const unsigned vectors[] = { 0x20010000, ( unsigned ) &Reset_Handler };

namespace demo
{
    unsigned overloaded(unsigned n) { ++calls; return n; }
    unsigned overloaded(int n) { ++calls; return n; }
    unsigned pointer(unsigned *p) { ++calls; return *p; }
    float floating(unsigned n) { ++calls; return 1.0f; }
    void clear() { ++calls; }
}
