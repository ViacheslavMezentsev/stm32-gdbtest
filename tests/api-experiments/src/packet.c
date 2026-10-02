#include "app.h"

int32_t read_packet( uint8_t* output, uint32_t capacity )
{
    if ( capacity < sizeof( sample.bytes ) )
    {
        return -1;
    }
    for ( uint32_t i = 0; i < sizeof( sample.bytes ); i++ )
    {
        output[i] = sample.bytes[i];
    }
    return ( int32_t ) sizeof( sample.bytes );
}
