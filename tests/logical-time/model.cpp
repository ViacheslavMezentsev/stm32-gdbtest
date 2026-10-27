#include "model.hpp"
Model state;

extern "C" void model_reset()
{
    state = { 0x13579BDF, IDLE, 0, 0, 0, 0, 0, 0x2468ACE0 };
}

extern "C" unsigned start( uint32_t now, uint32_t delay )
{
    // Допуск: 1..2^31-1 тиков; повторный start активного автомата не меняет состояние.
    if ( state.phase == WAITING || delay == 0 || delay >= 0x80000000u ) return 0;
    if ( DEFECT != 3 || state.phase != FAILED ) state.started = now;
    state.delay = delay;
    state.phase = WAITING;
    ++state.attempts;
    return 1;
}

extern "C" unsigned poll( uint32_t now )
{
    if ( state.phase != WAITING ) return state.phase;
    // Вычитание uint32_t определено по модулю 2^32. Полный оборот без poll недопустим.
    const uint32_t elapsed = now - state.started;
    const bool due         = DEFECT == 1   ? elapsed > state.delay
                             : DEFECT == 2 ? now >= uint32_t( state.started + state.delay )
                                           : elapsed >= state.delay;
    if ( due )
    {
        state.phase = DONE;
        ++state.successes;
    }
    return state.phase;
}

extern "C" void fail()
{
    if ( state.phase != WAITING ) return;
    state.phase = FAILED;
    ++state.failures;
}
