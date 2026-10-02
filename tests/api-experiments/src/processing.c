#include "app.h"

struct Packet packet = { 1, { 0 }, 7 };
volatile int32_t packet_status;
volatile uint32_t packet_total;

void process_packet( void )
{
    int32_t status = read_packet( packet.data, sizeof( packet.data ) );
    packet_status  = status;
    if ( status == ( int32_t ) sizeof( packet.data ) )
    {
        uint32_t total = 0;
        for ( uint32_t i = 0; i < sizeof( packet.data ); i++ )
        {
            total += packet.data[i];
        }
        packet_total = total;
    }
}

uint32_t process_sample( const struct Sample* input, uint32_t sequence )
{
    uint32_t offset = sequence + ( uint32_t ) input->mode;
    uint32_t total  = sum_bytes( input->bytes, sizeof( input->bytes ), offset );
    return total ^ ( uint32_t ) input->signed_value;
}

struct ReturnPair pair_input = { -7, 19 };
volatile uint64_t accepted_wide;
volatile float accepted_gain;
volatile struct ReturnPair accepted_pair;

void process_returns( void )
{
    accepted_wide = calculate_wide( sample.wide_value );
    accepted_gain = calculate_gain( sample.gain );
    accepted_pair = transform_pair( pair_input );
}

volatile uint32_t route_a_result;
volatile uint32_t route_b_result;

void process_routes( void )
{
    route_a_result = route_alpha();
    route_b_result = route_beta();
}
