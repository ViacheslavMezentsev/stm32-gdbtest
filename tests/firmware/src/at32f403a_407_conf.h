/* SDK configuration for the CI firmware: register types of the peripherals it touches, no driver sources. */
#ifndef AT32F403A_407_CONF_H
#define AT32F403A_407_CONF_H

#define HEXT_VALUE           ( ( uint32_t ) 8000000 )
#define HEXT_STARTUP_TIMEOUT ( ( uint16_t ) 0x3000 )
#define HICK_VALUE           ( ( uint32_t ) 8000000 )
#define LEXT_VALUE           ( ( uint32_t ) 32768 )

#include "at32f403a_407_crm.h"
#include "at32f403a_407_tmr.h"
#include "at32f403a_407_rtc.h"
#include "at32f403a_407_gpio.h"
#include "at32f403a_407_pwc.h"
#include "at32f403a_407_adc.h"
#include "at32f403a_407_dma.h"
#include "at32f403a_407_debug.h"
#include "at32f403a_407_exint.h"
#include "at32f403a_407_misc.h"

#endif
