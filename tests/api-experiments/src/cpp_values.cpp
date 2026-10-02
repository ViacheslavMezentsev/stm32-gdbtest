#include "cpp_values.hpp"

Small small_transform( Small input )
{
    return { input.value + 10 };
}

Pair pair_transform( Pair input )
{
    return { input.code - 1, input.count + 1 };
}

Hfa hfa_transform( Hfa input )
{
    return { input.x + 1.0f, input.y + 2.0f };
}

int Converter::apply( int input ) const
{
    return input + bias;
}

float Converter::apply( float input ) const
{
    return input + bias;
}
