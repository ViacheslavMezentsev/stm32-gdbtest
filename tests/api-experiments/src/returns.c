#include "app.h"

uint64_t calculate_wide( uint64_t value )
{
    return value + 9;
}

float calculate_gain( float value )
{
    return value + 1.25f;
}

struct ReturnPair transform_pair( struct ReturnPair input )
{
    struct ReturnPair result = { input.code - 1, input.count + 1 };
    return result;
}
