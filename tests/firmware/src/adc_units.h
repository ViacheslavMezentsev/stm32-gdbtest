/* Pure measurement arithmetic; quality describes provenance, not accuracy. */
#ifndef ADC_UNITS_H
#define ADC_UNITS_H
#include <stdint.h>

typedef struct
{
    uint32_t vdda_mv;
    int32_t temperature_mdeg_c;
    uint32_t quality;
} adc_reading_t;

adc_reading_t adc_convert_f030( uint16_t temperature, uint16_t reference, uint16_t reference_cal, uint16_t temperature_cal );
adc_reading_t adc_convert_f103( uint16_t temperature, uint16_t reference );
adc_reading_t adc_convert_f4_factory( uint16_t temperature, uint16_t reference, uint16_t reference_cal, uint16_t temperature_cal1,
    uint16_t temperature_cal2 );
#endif
