#include "app.h"

struct Sample sample = {
    -123, UINT64_C( 0x123456789abcdef0 ), 3.5f, MODE_ACTIVE, "sensor", { 0, 1, 2, 3, 127, 128, 254, 255 }
};
volatile uint32_t cycles;
volatile uint32_t checksum;

int main( void )
{
    for ( ;; )
    {
        checksum = process_sample( &sample, cycles );
        process_packet();
        process_returns();
        cycles++;
    }
}

uint32_t sum_bytes( const uint8_t* data, uint32_t count, uint32_t seed )
{
    uint32_t total = seed;
    for ( uint32_t i = 0; i < count; i++ )
    {
        total += data[i];
    }
    return total;
}
