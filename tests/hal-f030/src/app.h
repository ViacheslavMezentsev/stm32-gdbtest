#pragma once
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
void init( void );
void setup( void );
void loop( void );
void app_idle( uint32_t milliseconds );

/* Numeric units describe representation, not measurement accuracy. */
typedef enum
{
    ADC_INVALID              = 0,
    ADC_TYPICAL              = 1,
    ADC_FACTORY              = 2,
    ADC_FACTORY_SINGLE_POINT = 3
} AdcQuality;

typedef struct
{
    uint32_t vdda_mv;
    int32_t temperature_mdeg_c;
    AdcQuality quality;
} AdcReading;

AdcReading adc_convert_typical( uint16_t temperature, uint16_t reference );
AdcReading adc_convert_factory( uint16_t temperature, uint16_t reference, uint16_t reference_cal, uint16_t temperature_cal1,
    uint16_t temperature_cal2 );
AdcReading adc_convert_single_point( uint16_t temperature, uint16_t reference, uint16_t reference_cal, uint16_t temperature_cal );
AdcReading platform_adc_convert( uint16_t temperature, uint16_t reference );

typedef struct
{
    uint32_t adc_sequences;
    uint32_t timer_events;
    uint32_t rtc_events;
    uint16_t temperature_raw;
    uint16_t vrefint_raw;
    AdcReading measurement;
} AppState;

extern volatile AppState app_state;
/* Platform ADC contract: one DMA sequence, temperature then VREFINT, aligned buffer of two samples. */
void platform_adc_start( volatile uint16_t* samples );
void platform_adc_stop( void );
void platform_timer_start( void );
void platform_led_toggle( void );
void platform_sleep( void );
uint32_t platform_ticks( void );
void platform_error( void );
void app_adc_complete( void );
void app_timer_event( void );
void app_rtc_event( void );
void platform_adc_prepare( void );
void platform_rtc_prepare( void );
void platform_rtc_arm( void );
#ifdef __cplusplus
}
#endif
