/* Minimal application API observed by the CI contracts (no HAL). */
#ifndef APP_H
#define APP_H

#include <stdint.h>

typedef enum
{
    APP_MODE_IDLE  = 0,
    APP_MODE_BLINK = 1
} app_mode_t;

typedef struct
{
    uint32_t ticks;
    uint8_t led;
} app_state_t;

/* Observed result of the producer call made by the receiver module. */
typedef struct
{
    uint32_t produced;
    uint32_t calls;
    uint32_t took_zero_branch;
} app_receiver_state_t;

extern volatile app_state_t app_state;
extern volatile app_receiver_state_t app_received;
extern volatile uint32_t app_delay;

void board_init( void );
void board_led_toggle( void );
void board_delay_ms( uint32_t delay_ms );
void board_adc_init( void );
void board_adc_sample( void );
void board_rtc_init( void );
#if defined( STM32F103xB )
void board_rtc_service( void );
#endif
uint32_t app_step( app_state_t* state, app_mode_t mode );
/* Call the producer and record its return value for the observing scenario. */
void app_receiver_step( void );
void app_loop( void );

#endif
