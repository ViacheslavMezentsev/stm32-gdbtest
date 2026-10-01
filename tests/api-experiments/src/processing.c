#include "app.h"

uint32_t process_sample( const struct Sample* input, uint32_t sequence )
{
    uint32_t offset = sequence + ( uint32_t ) input->mode;
    uint32_t total  = sum_bytes( input->bytes, sizeof( input->bytes ), offset );
    return total ^ ( uint32_t ) input->signed_value;
}
