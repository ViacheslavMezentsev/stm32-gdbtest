#include "model.hpp"
#include <cstdio>
int failures = 0;

void check( bool ok, const char* name )
{
    std::printf( "%s %s\n", ok ? "PASS" : "FAIL", name );
    if ( !ok ) ++failures;
}

void packet( unsigned length, unsigned first )
{
    feed( length );
    for ( unsigned i = 0; i < length; ++i )
        feed( first + i );
}

int main()
{
    model_reset();
    packet( 3, 10 );
    packet( 2, 70 );
    check( state.packets == 2 && state.published_size == 2 && state.published[0] == 70 && state.published[1] == 71 && state.used == 0,
        "next-after-complete" );
    model_reset();
    feed( 4 );
    feed( 20 );
    expire();
    packet( 2, 80 );
    check( state.packets == 1 && state.published_size == 2 && state.published[0] == 80 && state.published[1] == 81, "next-after-timeout" );
    for ( unsigned order = 0; order < 2; ++order )
    {
        model_reset();
        for ( unsigned i = 0; i < 6; ++i )
            enqueue( i );
        kick();
        complete();
        for ( unsigned i = 10; i < 14; ++i )
            enqueue( i );
        kick();
        check( state.inflight == 2, "wrap-first-segment" );
        receive_error();
        check( state.busy == 1 && state.inflight == 2, "rx-keeps-tx" );
        if ( !order ) kick();
        complete();
        if ( order ) kick();
        check( state.busy == 1 && state.inflight == 2, "wrap-next-segment" );
        complete();
        complete();
        bool same = state.sent_size == 10;
        for ( unsigned i = 0; i < 10 && same; ++i )
            same = state.sent[i] == ( i < 6 ? i : i + 4 );
        check( same && !state.busy && !state.count, "wrap-order-exact-output" );
    }
    model_reset();
    enqueue( 41 );
    kick();
    enqueue( 42 );
    kick();
    check( state.inflight == 1, "busy-kick-preserves-owned-segment" );
    complete();
    complete();
    check( state.sent_size == 2 && state.sent[0] == 41 && state.sent[1] == 42, "next-tx" );
    model_reset();
    for ( unsigned i = 0; i < 8; ++i )
        check( enqueue( i ) == 1, "capacity-accepted" );
    check( enqueue( 9 ) == 0 && state.count == 8, "capacity-refused" );
    check( state.guard_a == 0x13579BDF && state.guard_b == 0x2468ACE0, "guards" );
    std::printf( "failures=%d\n", failures );
    return failures ? 1 : 0;
}
