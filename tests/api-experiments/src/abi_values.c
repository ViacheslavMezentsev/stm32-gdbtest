#include "abi_values.h"

volatile uint32_t accumulated;

void accumulate( uint32_t increment )
{
    accumulated += increment;
}

double affine( double input, double offset )
{
    return input * 2.0 + offset;
}

float gain_adjust( float input )
{
    return input + 1.25f;
}

uint32_t weighted_sum( uint32_t a, uint32_t b, uint32_t c, uint32_t d, uint32_t e, uint32_t f )
{
    return a + 10 * b + 100 * c + 1000 * d + 10000 * e + 100000 * f;
}
