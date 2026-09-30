#include "app.h"

volatile AppState app_state = {};
alignas( 4 ) static volatile uint16_t adc_samples[2];
static volatile bool adc_ready;
static uint32_t rtc_handled;

void init( void )
{
}

void setup( void )
{
    platform_adc_prepare();
    platform_rtc_prepare();
    platform_rtc_arm();
    platform_timer_start();
}

void loop( void )
{
    adc_ready = false;
    platform_adc_start( adc_samples );
    const uint32_t started = platform_ticks();
    while ( !adc_ready )
    {
        if ( ( uint32_t ) ( platform_ticks() - started ) >= 100 ) platform_error();
    }
    platform_adc_stop();
    app_state.temperature_raw                = adc_samples[0];
    app_state.vrefint_raw                    = adc_samples[1];
    const AdcReading reading                 = platform_adc_convert( app_state.temperature_raw, app_state.vrefint_raw );
    app_state.measurement.vdda_mv            = reading.vdda_mv;
    app_state.measurement.temperature_mdeg_c = reading.temperature_mdeg_c;
    app_state.measurement.quality            = reading.quality;
    ++app_state.adc_sequences;
    const uint32_t events = app_state.rtc_events;
    if ( events != rtc_handled )
    {
        platform_rtc_arm();
        rtc_handled = events;
    }
    platform_led_toggle();
    app_idle( 500 );
}

// Keep SysTick enabled: it wakes the CPU and advances the idle deadline.
// Ordinary Sleep preserves clocks; Stop and clock restoration are separate policies.
void app_idle( uint32_t milliseconds )
{
    const uint32_t started = platform_ticks();
    while ( ( uint32_t ) ( platform_ticks() - started ) < milliseconds )
    {
        platform_sleep();
    }
}

void app_adc_complete( void )
{
    adc_ready = true;
}

void app_timer_event( void )
{
    ++app_state.timer_events;
}

void app_rtc_event( void )
{
    ++app_state.rtc_events;
}
