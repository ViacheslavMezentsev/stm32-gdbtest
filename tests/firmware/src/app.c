#include "app.h"

volatile app_state_t app_state;
/* Initialized data keeps a non-empty .data load section in Flash. */
volatile uint32_t app_delay = 500U;
/* Version and board in Flash, and a RAM copy made at start: a string field, a string pointer
   and two memory blocks with the same bytes for the string checks of the scenarios. */
const app_info_t app_info = { "v1.2.0-ci", "stm32-gdbtest-ci" };
volatile char app_version_ram[APP_VERSION_SIZE];

uint32_t app_step( app_state_t* state, app_mode_t mode )
{
    state->ticks++;
    if ( mode == APP_MODE_BLINK )
    {
        state->led ^= 1U;
    }
    return state->ticks;
}

void app_loop( void )
{
    /* The receiver consumes the producer's return value; app_state is published inside it. */
    app_receiver_step();
    board_led_toggle();
#if defined( STM32F103xB ) || defined( AT32F403ACGU7 )
    board_rtc_service();
#endif
    board_adc_sample();
    board_delay_ms( app_delay );
}

int main( void )
{
    /* Element-wise volatile copy: no memcpy, the firmware links without the C library. */
    for ( uint32_t i = 0U; i < APP_VERSION_SIZE; i++ )
    {
        app_version_ram[i] = app_info.version[i];
    }
    board_init();
    for ( ;; )
    {
        app_loop();
    }
}
