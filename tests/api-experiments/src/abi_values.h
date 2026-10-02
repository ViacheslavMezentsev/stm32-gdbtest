#ifndef ABI_VALUES_H
#define ABI_VALUES_H
#include <stdint.h>

extern volatile uint32_t accumulated;
extern volatile double accepted_double;
extern volatile float accepted_float;
extern volatile uint32_t accepted_stack;
extern volatile uint32_t abi_cycles;
void accumulate( uint32_t increment );
double affine( double input, double offset );
float gain_adjust( float input );
uint32_t weighted_sum( uint32_t a, uint32_t b, uint32_t c, uint32_t d, uint32_t e, uint32_t f );
void process_abi( void );
#endif
