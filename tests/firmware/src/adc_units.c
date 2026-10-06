#include "adc_units.h"
#include <limits.h>

static int valid_raw( uint16_t value )
{
    return value > 0U && value < 4095U;
}

adc_reading_t adc_convert_f030( uint16_t temperature, uint16_t reference, uint16_t reference_cal, uint16_t temperature_cal )
{
    const adc_reading_t invalid = { 0U, 0, 0U };
    if ( !valid_raw( temperature ) || !valid_raw( reference ) || !valid_raw( reference_cal ) || !valid_raw( temperature_cal ) )
    {
        return invalid;
    }
    /* DS9773: calibration at 3.3 V / 30 C; typical negative slope 4.3 mV/C. */
    const uint32_t vdda = 3300U * reference_cal / reference;
    /* Application window; not a universal STM32 operating range. */
    if ( vdda < 2400U || vdda > 3600U )
    {
        return invalid;
    }
    const int64_t delta          = ( ( int64_t ) temperature_cal * reference - ( int64_t ) temperature * reference_cal ) * 3300000000LL;
    const int32_t temperature_mc = 30000 + delta / ( 4095LL * reference * 4300LL );
    const adc_reading_t result   = { vdda, temperature_mc, 3U };
    return result;
}

adc_reading_t adc_convert_f103( uint16_t temperature, uint16_t reference )
{
    const adc_reading_t invalid = { 0U, 0, 0U };
    if ( !valid_raw( temperature ) || !valid_raw( reference ) )
    {
        return invalid;
    }
    /* DS5319 typical values: VREFINT=1.20 V, V25=1.43 V, negative slope=4.3 mV/C. */
    const uint32_t vdda = 1200U * 4095U / reference;
    if ( vdda < 2400U || vdda > 3600U )
    {
        return invalid;
    }
    const int64_t delta          = ( 1430000LL * reference - 1200000LL * temperature ) * 1000LL;
    const int32_t temperature_mc = 25000 + delta / ( 4300LL * reference );
    const adc_reading_t result   = { vdda, temperature_mc, 1U };
    return result;
}

adc_reading_t adc_convert_f4_factory( uint16_t temperature, uint16_t reference, uint16_t reference_cal, uint16_t temperature_cal1,
    uint16_t temperature_cal2 )
{
    const adc_reading_t invalid = { 0U, 0, 0U };
    if ( !valid_raw( temperature ) || !valid_raw( reference ) || !valid_raw( reference_cal ) || !valid_raw( temperature_cal1 ) ||
         !valid_raw( temperature_cal2 ) || temperature_cal2 <= temperature_cal1 )
    {
        return invalid;
    }
    const uint32_t vdda = 3300U * reference_cal / reference;
    if ( vdda < 2400U || vdda > 3600U )
    {
        return invalid;
    }
    const int64_t delta   = ( ( int64_t ) temperature * reference_cal - ( int64_t ) temperature_cal1 * reference ) * 80000LL;
    const int64_t degrees = 30000 + delta / ( ( int64_t ) ( temperature_cal2 - temperature_cal1 ) * reference );
    if ( degrees < INT32_MIN || degrees > INT32_MAX )
    {
        return invalid;
    }
    const adc_reading_t result = { vdda, ( int32_t ) degrees, 2U };
    return result;
}

adc_reading_t adc_convert_at32f403a( uint16_t temperature, uint16_t reference )
{
    const adc_reading_t invalid = { 0U, 0, 0U };
    if ( !valid_raw( temperature ) || !valid_raw( reference ) )
    {
        return invalid;
    }
    /* RM AT32F403A/407 19.4.1.2: VINTRV typical 1.2 V. Artery SDK example adc/internal_temperature_sensor:
       V25 = 1.26 V, slope -4.23 mV/C in T = (V25 - Vsense) / slope + 25, so Vsense rises with temperature. */
    const uint32_t vdda = 1200U * 4095U / reference;
    if ( vdda < 2400U || vdda > 3600U )
    {
        return invalid;
    }
    const int64_t delta          = ( 1200000LL * temperature - 1260000LL * reference ) * 1000LL;
    const int32_t temperature_mc = 25000 + delta / ( 4230LL * reference );
    const adc_reading_t result   = { vdda, temperature_mc, 4U };
    return result;
}
