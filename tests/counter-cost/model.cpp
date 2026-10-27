#include "model.hpp"
Model state;

extern "C" void model_reset()
{
    state = { 0x13579BDF, 250, 0, 0, 0, 0, 0, 0, 0x2468ACE0 };
}

extern "C" unsigned difference( uint32_t before, uint32_t after, uint32_t upper, uint32_t complete )
{
    state.valid = 0;
    state.delta = 0;
    // Верхняя граница задаётся независимым условием опыта, а не самим счётчиком.
    if ( before > 255 || after > 255 ) return 0;
    if ( DEFECT != 3 && ( !complete || upper >= 256 ) ) return 0;
    const uint32_t delta = DEFECT == 1 ? after - before : ( after - before ) & 255u;
    if ( DEFECT != 3 && delta > upper ) return 0;
    state.delta = delta;
    state.valid = 1;
    return 1;
}

extern "C" unsigned measure( uint32_t work )
{
    if ( work > 16 ) return 0;
    // Два чтения стоят по 3 учебных тика. В интервал входит только первое.
    const uint32_t before = state.clock;
    state.clock           = ( state.clock + 3 + 7 * work ) & 255u;
    const uint32_t after  = state.clock;
    state.clock           = ( state.clock + 3 ) & 255u;
    state.gross           = ( after - before ) & 255u;
    state.baseline        = 3;
    state.observer        = 6;
    state.net             = DEFECT == 2 ? state.gross : state.gross - state.baseline;
    return 1;
}
