#include "app.h"
#include <limits.h>

static bool valid_raw( uint16_t value )
{
    return value > 0 && value < 4095;
}

// Application operating window, not a universal STM32 ADC limit.
static bool valid_supply( uint32_t millivolts )
{
    return millivolts >= 2400 && millivolts <= 3600;
}

AdcReading adc_convert_typical( uint16_t temperature, uint16_t reference )
{
    if ( !valid_raw( temperature ) || !valid_raw( reference ) ) return {};
    // STM32F103 DS5319: VREFINT=1.20 V, V25=1.43 V, slope=4.3 mV/C (typical).
    const uint32_t vdda = 1200U * 4095U / reference;
    if ( !valid_supply( vdda ) ) return {};
    // Use the raw ratio to avoid losing precision through rounded VDDA.
    const int64_t delta   = ( 1430000LL * reference - 1200000LL * temperature ) * 1000;
    const int32_t degrees = 25000 + delta / ( 4300LL * reference );
    return { vdda, degrees, ADC_TYPICAL };
}

AdcReading adc_convert_factory( uint16_t temperature, uint16_t reference, uint16_t reference_cal, uint16_t temperature_cal1,
    uint16_t temperature_cal2 )
{
    if ( !valid_raw( temperature ) || !valid_raw( reference ) || !valid_raw( reference_cal ) || !valid_raw( temperature_cal1 ) ||
         !valid_raw( temperature_cal2 ) || temperature_cal2 <= temperature_cal1 )
        return {};
    // F411 DS10314: all factory samples at VDDA=3.3 V; temperature anchors 30/110 C.
    const uint32_t vdda = 3300U * reference_cal / reference;
    if ( !valid_supply( vdda ) ) return {};
    const int64_t delta   = ( int64_t( temperature ) * reference_cal - int64_t( temperature_cal1 ) * reference ) * 80000;
    const int64_t degrees = 30000 + delta / ( int64_t( temperature_cal2 - temperature_cal1 ) * reference );
    if ( degrees < INT32_MIN || degrees > INT32_MAX ) return {};
    return { vdda, int32_t( degrees ), ADC_FACTORY };
}

AdcReading adc_convert_single_point( uint16_t temperature, uint16_t reference, uint16_t reference_cal, uint16_t temperature_cal )
{
    if ( !valid_raw( temperature ) || !valid_raw( reference ) || !valid_raw( reference_cal ) || !valid_raw( temperature_cal ) ) return {};
    // F030 DS9773: TS_CAL1 at 30 C / 3.3 V; negative typical slope 4.3 mV/C.
    // VDDA uses factory VREFINT_CAL; temperature still relies on a typical slope.
    const uint32_t vdda = 3300U * reference_cal / reference;
    if ( !valid_supply( vdda ) ) return {};
    const int64_t delta   = ( int64_t( temperature_cal ) * reference - int64_t( temperature ) * reference_cal ) * 3300000000LL;
    const int32_t degrees = 30000 + delta / ( 4095LL * reference * 4300LL );
    return { vdda, degrees, ADC_FACTORY_SINGLE_POINT };
}
