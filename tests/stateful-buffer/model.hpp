#pragma once
// Нейтральная логика: нет UART, DMA, IRQ и динамической памяти.
#ifndef DEFECT
#define DEFECT 0
#endif
struct Model
{
    unsigned guard_a;
    unsigned wanted, used, packets, published_size;
    unsigned char pending[8], published[8];
    unsigned head, tail, count, busy, inflight, sent_size;
    unsigned char ring[8], sent[32];
    unsigned guard_b;
};

extern Model state;
extern "C" void model_reset();
extern "C" unsigned feed( unsigned value );
extern "C" void expire();
extern "C" unsigned enqueue( unsigned value );
extern "C" void kick();
extern "C" void complete();
extern "C" void receive_error();
