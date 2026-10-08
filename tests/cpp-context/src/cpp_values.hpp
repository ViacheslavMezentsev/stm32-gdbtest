#ifndef CPP_VALUES_HPP
#define CPP_VALUES_HPP
#include <stdint.h>

struct Small
{
    uint32_t value;
};

struct Pair
{
    int32_t code;
    uint32_t count;
};

struct Hfa
{
    float x;
    float y;
};

Small small_transform( Small input );
Pair pair_transform( Pair input );
Hfa hfa_transform( Hfa input );

struct Converter
{
    int bias;
    int apply( int input ) const;
    float apply( float input ) const;
};

extern Small small_input;
extern Pair pair_input;
extern Hfa hfa_input;
extern Converter converter;
extern "C" void process_cpp( void );
#endif
