#include "model.hpp"
#include <cstdio>
int failures = 0;

void check( bool ok, const char* name )
{
    std::printf( "%s %s\n", ok ? "PASS" : "FAIL", name );
    if ( !ok ) ++failures;
}

int main()
{
    model_reset();
    difference( 250, 5, 11, 1 );
    check( state.valid == 1 && state.delta == 11, "wrap" );
    difference( 7, 7, 0, 1 );
    check( state.valid == 1 && state.delta == 0, "valid-zero" );
    difference( 0, 255, 255, 1 );
    check( state.valid == 1 && state.delta == 255, "largest-valid" );
    difference( 7, 7, 256, 1 );
    check( state.valid == 0, "full-wrap-unknown" );
    difference( 7, 9, 2, 0 );
    check( state.valid == 0, "missing-unknown" );
    difference( 7, 12, 4, 1 );
    check( state.valid == 0, "bound-violated" );
    difference( 256, 0, 1, 1 );
    check( state.valid == 0, "range" );
    model_reset();
    measure( 0 );
    check( state.gross == 3 && state.baseline == 3 && state.net == 0 && state.observer == 6, "empty-cost" );
    measure( 4 );
    check( state.gross == 31 && state.net == 28 && state.observer == 6, "work-cost" );
    check( state.clock == 34, "total-cost" );
    check( measure( 17 ) == 0 && state.clock == 34, "work-refused" );
    check( state.guard_a == 0x13579BDF && state.guard_b == 0x2468ACE0, "guards" );
    return failures ? 1 : 0;
}
