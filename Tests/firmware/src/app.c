#include "app.h"

volatile app_state_t app_state;
/* Initialized data keeps a non-empty .data load section in Flash. */
volatile uint32_t app_delay = 200000U;

uint32_t app_step(app_state_t *state, app_mode_t mode)
{
    state->ticks++;
    if (mode == APP_MODE_BLINK)
    {
        state->led ^= 1U;
    }
    return state->ticks;
}

void app_loop(void)
{
    app_state_t next = app_state;
    (void)app_step(&next, APP_MODE_BLINK);
    app_state = next;
    board_led_toggle();
    for (uint32_t delay = 0; delay < app_delay; ++delay)
    {
    }
}

int main(void)
{
    board_init();
    for (;;)
    {
        app_loop();
    }
}
