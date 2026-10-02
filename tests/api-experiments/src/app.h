#pragma once
#include <stdint.h>

enum Mode
{
    MODE_IDLE   = 0,
    MODE_ACTIVE = 3
};

struct Sample
{
    int32_t signed_value;
    uint64_t wide_value;
    float gain;
    enum Mode mode;
    char name[8];
    uint8_t bytes[8];
};
extern struct Sample sample;
extern volatile uint32_t cycles;
extern volatile uint32_t checksum;
uint32_t process_sample( const struct Sample* input, uint32_t sequence );
uint32_t sum_bytes( const uint8_t* data, uint32_t count, uint32_t seed );

struct Packet
{
    uint32_t format;
    uint8_t data[8];
    uint32_t destination;
};
extern struct Packet packet;
extern volatile int32_t packet_status;
extern volatile uint32_t packet_total;
int32_t read_packet( uint8_t* output, uint32_t capacity );
void process_packet( void );
