#include "cache_suite.hpp"
#include <cstdio>

struct Fake
{
    std::array<std::uint8_t, 32> data{};
    unsigned stores = 0;
    bool fail_read = false, fail_store = false, corrupt = false;

    bool read( std::uint8_t* out, std::size_t n )
    {
        if ( fail_read )
        {
            out[0] = 99;
            return false;
        }
        for ( std::size_t i = 0; i < n; ++i )
            out[i] = data[i];
        return true;
    }

    bool store( const std::uint8_t* in, std::size_t n )
    {
        ++stores;
        // Even a failed operation may have partially modified the backing storage.
        if ( fail_store )
        {
            data[0] = 99;
            return false;
        }
        for ( std::size_t i = 0; i < n; ++i )
            data[i] = in[i];
        if ( corrupt ) data[0] ^= 1;
        return true;
    }
};

int failures( unsigned& checks )
{
    Fake f;
    BufferedStore<32, Fake> c( f );
    REQUIRE( c.load() );
    std::uint8_t v = 7, got = 0;
    REQUIRE( c.write( 0, &v, 1 ) );
    f.fail_store = true;
    REQUIRE( !c.commit() && c.dirty() );
    REQUIRE( c.read( 0, &got, 1 ) && got == 7 );
    f.fail_store = false;
    f.corrupt    = true;
    REQUIRE( !c.commit() && c.dirty() );
    f.corrupt   = false;
    f.fail_read = true;
    REQUIRE( !c.commit() && c.dirty() );
    f.fail_read = false;
    REQUIRE( c.commit() && !c.dirty() && f.data[0] == 7 );
    f.fail_read = true;
    REQUIRE( !c.load() );
    REQUIRE( c.read( 0, &got, 1 ) && got == 7 );
    f.fail_read = false;
    v           = 9;
    REQUIRE( c.write( 0, &v, 1 ) );
    v = 7;
    REQUIRE( c.write( 0, &v, 1 ) && c.dirty() );
    REQUIRE( c.commit() );
    unsigned count = f.stores;
    {
        BufferedStore<32, Fake> local( f );
        REQUIRE( local.load() );
        v = 3;
        REQUIRE( local.write( 0, &v, 1 ) );
    }
    REQUIRE( f.stores == count && f.data[0] == 7 );
    return 0;
}

int main()
{
    unsigned checks = 0;
    Fake f;
    int line = basic_suite<32>( f, checks );
    if ( !line ) line = failures( checks );
    std::printf( "HOST checks=%u failure_line=%d\n", checks, line );
    return line ? 1 : 0;
}
