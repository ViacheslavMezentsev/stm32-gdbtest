#include <stdint.h>

volatile uint32_t input_a = 11;
volatile uint32_t input_b = 23;
volatile uint32_t gain    = 3;
volatile uint32_t output_a;
volatile uint32_t output_b;
volatile uint32_t iterations;

static inline uint32_t scale_channel( uint32_t input, uint32_t multiplier )
{
    uint32_t product = input * multiplier;
    return product + 7;
}

int main( void )
{
    for ( ;; )
    {
        output_a = scale_channel( input_a, gain );
        output_b = scale_channel( input_b, gain );
        iterations++;
    }
}
