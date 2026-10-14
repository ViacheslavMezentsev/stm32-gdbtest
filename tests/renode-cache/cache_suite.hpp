#pragma once
#include "buffered_store.hpp"
// Same contract sequence on host fake and MCU adapter. Returns failing source line.
#define REQUIRE( x )                   \
    do                                 \
    {                                  \
        ++checks;                      \
        if ( !( x ) ) return __LINE__; \
    } while ( 0 )

template<std::size_t N, class Adapter>
int basic_suite( Adapter& adapter, unsigned& checks )
{
    BufferedStore<N, Adapter> cache( adapter );
    std::array<std::uint8_t, N> before{}, after{};
    std::uint8_t byte = 0, change = 0x42;
    REQUIRE( !cache.read( 0, &byte, 1 ) );
    REQUIRE( !cache.write( 0, &change, 1 ) );
    REQUIRE( !cache.commit() );
    REQUIRE( cache.load() );
    REQUIRE( !cache.dirty() );
    REQUIRE( adapter.read( before.data(), N ) );
    REQUIRE( cache.write( 0, before.data(), N ) );
    REQUIRE( !cache.dirty() );
    REQUIRE( cache.commit() && adapter.stores == 0 );
    REQUIRE( cache.write( 3, &change, 1 ) );
    change = 0x17;
    REQUIRE( cache.write( N - 1, &change, 1 ) );
    REQUIRE( cache.dirty() );
    REQUIRE( !cache.load() );
    REQUIRE( adapter.read( after.data(), N ) && before == after );
    REQUIRE( !cache.write( N - 1, before.data(), 2 ) );
    REQUIRE( !cache.write( static_cast<std::size_t>( -1 ), before.data(), 1 ) );
    REQUIRE( !cache.write( 0, nullptr, 1 ) );
    REQUIRE( cache.write( N, nullptr, 0 ) );
    REQUIRE( !cache.read( N, &byte, 1 ) );
    REQUIRE( cache.commit() && !cache.dirty() && adapter.stores == 1 );
    REQUIRE( cache.commit() && adapter.stores == 1 );
    BufferedStore<N, Adapter> restored( adapter );
    REQUIRE( restored.load() );
    REQUIRE( restored.read( 0, after.data(), N ) );
    before[3]     = 0x42;
    before[N - 1] = 0x17;
    REQUIRE( before == after );
    return 0;
}
