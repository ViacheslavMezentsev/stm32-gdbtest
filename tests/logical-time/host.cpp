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
    start( 100, 10 );
    check( poll( 109 ) == WAITING, "threshold-minus-one" );
    check( poll( 110 ) == DONE, "threshold-exact" );
    check( poll( 111 ) == DONE && state.successes == 1, "threshold-plus-one" );
    model_reset();
    start( 100, 10 );
    check( poll( 111 ) == DONE && state.successes == 1, "threshold-skipped" );
    model_reset();
    start( 0xfffffff8u, 10 );
    check( poll( 0xffffffffu ) == WAITING, "wrap-before-zero" );
    check( poll( 1 ) == WAITING, "wrap-minus-one" );
    check( poll( 2 ) == DONE && state.successes == 1, "wrap-exact" );
    check( poll( 3 ) == DONE && state.successes == 1, "wrap-plus-one" );
    model_reset();
    start( 100, 10 );
    fail();
    fail();
    check( state.phase == FAILED && state.failures == 1 && state.successes == 0, "failure-once" );
    check( poll( 1000 ) == FAILED && state.successes == 0, "failure-sticky" );
    start( 1000, 10 );
    check( poll( 1009 ) == WAITING, "retry-minus-one" );
    check( poll( 1010 ) == DONE, "retry-exact" );
    check( poll( 1011 ) == DONE && state.successes == 1 && state.attempts == 2, "retry-once" );
    start( 2000, 5 );
    poll( 2006 );
    check( state.successes == 2 && state.attempts == 3 && state.failures == 1, "reentry-after-done" );
    model_reset();
    check( start( 0, 0 ) == 0 && start( 0, 0x80000000u ) == 0 && state.attempts == 0, "invalid-delay" );
    start( 42, 10 );
    check( start( 77, 20 ) == 0 && state.started == 42 && state.delay == 10 && state.attempts == 1, "busy-start" );
    check( state.guard_a == 0x13579BDF && state.guard_b == 0x2468ACE0, "guards" );
    return failures ? 1 : 0;
}
