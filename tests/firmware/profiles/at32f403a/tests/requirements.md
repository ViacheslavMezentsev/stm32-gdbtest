# CI scenario requirements (at32f403a)

## HW_CI_BOOT
At main, initialized delay is 500 ms and BSS counters are zero. After board initialization,
consecutive app_loop entries advance app_state.ticks by one.

## HW_CI_GPIO
At the first board_led_toggle, the GPIOC clock is enabled; PC13 is a push-pull output with moderate drive,
initially High (LED off on the active-low WeAct AT32F4 Core Board). This checks registers, not emitted light.

## HW_CI_CLOCK
HICK supplies nominal 8 MHz with AHB/APB1/APB2 divide-by-one. SystemCoreClock agrees;
SysTick uses core clock with LOAD=7999, enabled with IRQ. No frequency accuracy claim.

## HW_CI_BLINK
PC13 alternates across consecutive board_led_toggle entries, separated by at least
500 firmware milliseconds. Debugger stops are excluded from physical timing claims.

## HW_CI_TIM2_INIT
TMR2 uses internal 8 MHz clock, DIV=7999, PR=99 (nominal 100 ms), upcounting, overflow interrupt and counter
enabled. NVIC IRQ28 (TMR2_GLOBAL) is enabled and vector slot44 points to TIM2_IRQHandler.

## HW_CI_TIM2_IRQ
Natural TMR2 overflow enters exception44 with OVFIF set. Each handler publishes one event;
thread mode resumes. No software event or NVIC pending injection is used; no jitter claim.

## HW_CI_SYSTICK_IRQ
Natural SysTick enters exception15 through vector15. The handler increments the
millisecond counter once, then thread mode can resume. No external time reference.

## HW_CI_ADC_INIT
ADC1 PCLK2/2, ordinary scan IN16/IN17, 239.5 cycles, calibrated ADC on with VINTRV and temperature sensor;
normal halfword DMA1 channel1, IRQ11/vector27.

## HW_CI_ADC_DMA
Two natural scans deliver two halfwords each, exception27 with full transfer done and no transfer error; the ISR
publishes raw values before the sequence, DMA stops and flags clear.

## HW_CI_ADC_UNITS
Vendor-example provenance=4; plausible VDDA and die temperature. Values are estimates, not calibrated accuracy.

## HW_CI_ADC_VECTORS
Four analytic anchors of the vendor-example formula exercise adc_convert_at32f403a through argument injection;
exact integer output.

## HW_CI_ADC_INVALID
Zero, saturation, uint16 overflow-range and implausible VDDA inputs yield invalid reading; subsequent acquisition recovers.

## HW_CI_ADC_TIMEOUT
Mask DMA IRQ11: transfers complete but no notification; after at least 20 ticks enter error4 without stale publication.

## HW_CI_ADC_BUSY
Enable DMA channel before sample: ownership guard yields error6 without publication; this does not prove active ADC conversion.

## HW_CI_ADC_DISABLED
Clear ADC ADCEN before sample: error3 without publication. This is not a driver return-code injection.

## HW_CI_RTC_INIT
LICK, counter RTC divider 39999, initial alarm 2, EXINT17 rising, IRQ41/vector57; no battery-domain reset.

## HW_CI_RTC_ALARM
Two natural alarms enter exception57 with TAF/EXINT17 pending; thread service rearms, one event per handler,
application resumes.

## HW_CI_RTC_DEADLINE
Inject zero mask into the LICK-stable wait; error3 after at least 1000 ticks without changing the battery-domain
configuration or publishing events. Not a physical oscillator fault.

## HW_CI_SLEEP_SYSTICK
Ordinary Sleep/WFI interrupted by SysTick exception15 with external IRQs masked; interrupted frame follows WFI,
delay and ADC state retained.

## HW_CI_SLEEP_TIM2
With SysTick disabled and only TMR2 enabled, exception44 interrupts WFI; ticks do not advance, restore IRQ controls
and resume. Not Stop/current measurement.
