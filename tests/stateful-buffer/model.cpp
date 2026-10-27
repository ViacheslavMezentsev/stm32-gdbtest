#include "model.hpp"
Model state;

extern "C" void model_reset()
{
    // Явная инициализация работает и до startup стандартной библиотеки.
    auto* bytes = reinterpret_cast<unsigned char*>( &state );
    for ( unsigned i = 0; i < sizeof( state ); ++i )
        bytes[i] = 0;
    state.guard_a = 0x13579BDF;
    state.guard_b = 0x2468ACE0;
}

extern "C" unsigned feed( unsigned value )
{
    // Формат: длина 1..8, затем ровно столько байтов; контроль CRC здесь не моделируется.
    if ( !state.wanted )
    {
        if ( value < 1 || value > 8 ) return 0;
        state.wanted = value;
        return 1;
    }
    if ( state.used >= 8 ) return 0;
    state.pending[state.used++] = static_cast<unsigned char>( value );
    if ( state.used == state.wanted )
    {
        for ( unsigned i = 0; i < state.used; ++i )
            state.published[i] = state.pending[i];
        state.published_size = state.used;
        ++state.packets;
        state.wanted = 0;
        if ( DEFECT != 1 ) state.used = 0;    // Дефект: остаток завершённого пакета.
    }
    return 1;
}

extern "C" void expire()
{
    state.wanted = 0;
    if ( DEFECT != 1 ) state.used = 0;    // Дефект: остаток частичного пакета.
}

extern "C" unsigned enqueue( unsigned value )
{
    if ( state.count == 8 || value > 255 ) return 0;
    state.ring[state.head] = static_cast<unsigned char>( value );
    state.head             = ( state.head + 1 ) % 8;
    ++state.count;
    return 1;
}

extern "C" void kick()
{
    if ( state.busy && DEFECT != 2 ) return;
    if ( !state.count ) return;
    // Один непрерывный сегмент: очередь может продолжаться с нулевого индекса.
    state.inflight = state.count < 8 - state.tail ? state.count : 8 - state.tail;
    state.busy     = 1;
}

extern "C" void complete()
{
    if ( !state.busy ) return;
    if ( state.sent_size + state.inflight > 32 ) return;
    for ( unsigned i = 0; i < state.inflight; ++i )
        state.sent[state.sent_size++] = state.ring[state.tail + i];
    state.tail      = ( state.tail + state.inflight ) % 8;
    state.count    -= state.inflight;
    state.busy      = 0;
    state.inflight  = 0;
    kick();    // Продолжение сегмента из обработчика завершения.
}

extern "C" void receive_error()
{
    expire();    // Ошибка RX не должна менять очередь TX.
}
