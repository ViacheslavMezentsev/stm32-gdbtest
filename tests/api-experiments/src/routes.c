#include "app.h"

uint32_t walk_route( uint32_t depth, uint32_t seed )
{
    if ( depth == 0 )
    {
        return seed;
    }
    return walk_route( depth - 1, seed + 10 ) + depth;
}

uint32_t route_alpha( void )
{
    return walk_route( 2, 1 ) + 100;
}

uint32_t route_beta( void )
{
    return walk_route( 3, 2 ) + 200;
}
