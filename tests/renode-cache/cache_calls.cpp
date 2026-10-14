#include "cache_suite.hpp"
extern "C" {
extern unsigned _stack_top, _sbss, _ebss;
void reset_handler();

void fault_handler()
{
    for ( ;; )
    {
    }
}

__attribute__( ( section( ".vectors" ), used ) )
const void* vectors[]    = { &_stack_top, ( void* ) reset_handler, ( void* ) fault_handler, ( void* ) fault_handler };
volatile unsigned checks = 0, failure_line = 0, stores_seen = 0, programs_seen = 0, guard_ok = 0;

__attribute__( ( noinline ) ) void cache_done()
{
    __asm volatile( "nop" );
}

int memcmp( const void* a, const void* b, unsigned n )
{
    auto x = ( const unsigned char* ) a;
    auto y = ( const unsigned char* ) b;
    while ( n-- )
    {
        if ( *x != *y ) return *x - *y;
        ++x;
        ++y;
    }
    return 0;
}

void* memset( void* p, int c, unsigned n )
{
    auto q = ( unsigned char* ) p;
    while ( n-- )
        *q++ = ( unsigned char ) c;
    return p;
}

void* memcpy( void* d, const void* s, unsigned n )
{
    auto a = ( unsigned char* ) d;
    auto b = ( const unsigned char* ) s;
    while ( n-- )
        *a++ = *b++;
    return d;
}
}

struct Flash
{
    unsigned stores = 0, programs = 0;

    static volatile unsigned& reg( unsigned offset ) { return *( volatile unsigned* ) ( 0x40022000 + offset ); }

    bool read( std::uint8_t* out, std::size_t n )
    {
        auto src = ( volatile std::uint8_t* ) 0x0800F800;
        for ( std::size_t i = 0; i < n; ++i )
            out[i] = src[i];
        return true;
    }

    bool store( const std::uint8_t* in, std::size_t n )
    {
        if ( n != 2048 ) return false;
        reg( 8 ) = 0x45670123;
        reg( 8 ) = 0xCDEF89AB;
        if ( reg( 0x14 ) & 0x80000000 ) return false;
        reg( 0x10 ) = 1;
        reg( 0x14 ) = ( 31u << 3 ) | 2u | 0x10000u;
        if ( !( reg( 0x10 ) & 1 ) ) return false;
        // Verify actual erase, rather than trusting EOP alone.
        for ( unsigned i = 0; i < 2048; ++i )
            if ( ( ( volatile unsigned char* ) 0x0800F800 )[i] != 255 ) return false;
        ++stores;
        for ( unsigned i = 0; i < 2048; i += 8 )
        {
            reg( 0x10 ) = 1;
            auto dst    = ( volatile unsigned char* ) ( 0x0800F800 + i );
            for ( unsigned j = 0; j < 8; ++j )
                dst[j] = in[i + j];
            reg( 0x14 ) = 1;
            if ( !( reg( 0x10 ) & 1 ) ) return false;
            ++programs;
        }
        reg( 0x14 ) = 0x80000000;
        return true;
    }
};

extern "C" void reset_handler()
{
    for ( auto p = &_sbss; p < &_ebss; ++p )
        *p = 0;
    Flash adapter;
    unsigned local = 0;
    failure_line   = basic_suite<2048>( adapter, local );
    checks         = local;
    stores_seen    = adapter.stores;
    programs_seen  = adapter.programs;
    guard_ok       = ( *( volatile unsigned* ) 0x0800F7FC == 0x12345678 );
    BufferedStore<2048, Flash> interactive( adapter );
    interactive.load();
    std::uint8_t call_byte = 0x66;
    // Keep the constructed object and its input buffer alive for debugger-driven calls.
    cache_done();
    ( void ) call_byte;
    for ( ;; )
    {
    }
}
