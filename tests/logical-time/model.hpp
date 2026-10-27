#pragma once
#include <cstdint>
#ifndef DEFECT
#define DEFECT 0
#endif
// Время задаёт вызывающий код; таймеры, IRQ и планировщик не используются.
enum Phase : uint32_t
{
    IDLE    = 0,
    WAITING = 1,
    DONE    = 2,
    FAILED  = 3
};

struct Model
{
    uint32_t guard_a, phase, started, delay, attempts, successes, failures, guard_b;
};

extern Model state;
extern "C" void model_reset();
extern "C" unsigned start( uint32_t now, uint32_t delay );
extern "C" unsigned poll( uint32_t now );
extern "C" void fail();
