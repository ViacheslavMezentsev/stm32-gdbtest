/*
 * Application receiver of the producer's return value.
 *
 * RU: Обычный прикладной модуль: вызывает app_step и использует возвращённое значение —
 *     сохраняет его и различает нулевой и ненулевой исход. Существует, чтобы сценарий мог
 *     подтвердить перенос возвращённого значения вызывающему.
 * EN: An ordinary application module: it calls app_step and consumes the returned value — it stores
 *     it and distinguishes the zero from the non-zero outcome. It exists so that a scenario can
 *     confirm the transfer of a returned value to the caller.
 */
#include "app.h"

volatile app_receiver_state_t app_received;

/* Consume the producer's return value instead of discarding it. */
void app_receiver_step( void )
{
    app_state_t next        = app_state;
    const uint32_t produced = app_step( &next, APP_MODE_BLINK );

    app_received.produced = produced;
    app_received.calls++;
    app_received.took_zero_branch = ( produced == 0U ) ? 1U : 0U;
    app_state                     = next;
}
