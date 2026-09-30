#include "adc_units.h"

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
