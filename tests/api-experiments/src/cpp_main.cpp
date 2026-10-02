#include "cpp_values.hpp"

Small small_input   = { 10 };
Pair pair_input     = { -7, 19 };
Hfa hfa_input       = { 1.5f, 2.5f };
Converter converter = { 7 };
volatile Small small_sink;
volatile Pair pair_sink;
volatile Hfa hfa_sink;
volatile int int_sink;
volatile float float_sink;
volatile uint32_t cpp_cycles;

extern "C" void process_cpp( void )
{
    Small small      = small_transform( small_input );
    small_sink.value = small.value;
    Pair pair        = pair_transform( pair_input );
    pair_sink.code   = pair.code;
    pair_sink.count  = pair.count;
    Hfa hfa          = hfa_transform( hfa_input );
    hfa_sink.x       = hfa.x;
    hfa_sink.y       = hfa.y;
    int_sink         = converter.apply( 4 );
    float_sink       = converter.apply( 1.5f );
}

int main( void )
{
#if defined( __ARM_PCS_VFP )
    *( volatile uint32_t* ) 0xe000ed88 |= 0x00f00000;
    __asm volatile( "dsb\nisb" ::: "memory" );
#endif
    for ( ;; )
    {
        process_cpp();
        cpp_cycles++;
    }
}
