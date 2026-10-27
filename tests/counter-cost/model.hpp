#pragma once
#include <cstdint>
#ifndef DEFECT
#define DEFECT 0
#endif
// Учебные тики: не DWT, не циклы MCU и не длительность инструкций Renode.
struct Model
{
    uint32_t guard_a, clock, valid, delta, gross, baseline, net, observer, guard_b;
};

extern Model state;
extern "C" void model_reset();
extern "C" unsigned difference( uint32_t before, uint32_t after, uint32_t upper, uint32_t complete );
extern "C" unsigned measure( uint32_t work );
