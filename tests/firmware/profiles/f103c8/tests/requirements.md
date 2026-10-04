# CI scenario requirements (f103c8)

## HW_CI_BOOT
At main, initialized delay is 500 ms and BSS counters are zero. After board initialization,
consecutive app_loop entries advance app_state.ticks by one.

## HW_CI_GPIO
At the first board_led_toggle, GPIOB clock is enabled; PB2 is a 2 MHz push-pull output,
initially Low (LED off on WeAct BluePill-Plus). This checks registers, not emitted light.

## HW_CI_CLOCK
HSI supplies nominal 8 MHz with AHB/APB1/APB2 divide-by-one. SystemCoreClock agrees;
SysTick uses core clock with LOAD=7999, enabled with IRQ. No frequency accuracy claim.

## HW_CI_BLINK
PB2 alternates across consecutive board_led_toggle entries, separated by at least
500 firmware milliseconds. Debugger stops are excluded from physical timing claims.

## HW_CI_TIM2_INIT
TIM2 uses internal 8 MHz clock, PSC=7999, ARR=99 (nominal 100 ms), upcounting, UIE/CEN.
NVIC IRQ28 is enabled and vector slot44 points to TIM2_IRQHandler.

## HW_CI_TIM2_IRQ
Natural TIM2 update enters exception44 with UIF set. Each handler publishes one event;
thread mode resumes. No EGR/software-pending injection is used; no jitter claim.

## HW_CI_SYSTICK_IRQ
Natural SysTick enters exception15 through vector15. The handler increments the
millisecond counter once, then thread mode can resume. No external time reference.

## HW_CI_ADC_INIT
ADC1 PCLK2/2, independent regular scan CH16/17, 239.5 cycles, calibrated ADC on; normal halfword DMA1 channel1, IRQ11/vector27.

## HW_CI_ADC_DMA
Two natural scans deliver two halfwords each, exception27/TC without TE; ISR publishes raw values before sequence, DMA stops and flags clear.

## HW_CI_ADC_UNITS
Typical provenance=1; plausible VDDA and die temperature. Values are estimates, not factory-calibrated accuracy.

## HW_CI_ADC_VECTORS
Four fixed analytic anchors exercise adc_convert_f103 through argument injection; exact integer output.

## HW_CI_ADC_INVALID
Zero, saturation, uint16 overflow-range and implausible VDDA inputs yield invalid reading; subsequent acquisition recovers.

## HW_CI_ADC_TIMEOUT
Mask DMA IRQ11: transfers complete but no notification; after at least20 ticks enter error4 without stale publication.

## HW_CI_ADC_BUSY
Enable DMA channel before sample: ownership guard yields error6 without publication; this does not prove active ADC conversion.

## HW_CI_ADC_DISABLED
Clear ADC ADON before sample: error3 without publication. This is not a HAL return-code injection.

## HW_CI_RTC_INIT
LSI, counter RTC prescaler39999, initial alarm2, EXTI17 rising, IRQ41/vector57; no backup-domain reset.

## HW_CI_RTC_ALARM
Two natural alarms enter exception57 with ALRF/EXTI17 pending; thread service rearms, one event per handler, application resumes.

## HW_CI_RTC_DEADLINE
Inject zero mask into LSI-ready wait; error3 after at least1000 ticks without changing backup configuration or publishing events. Not a physical oscillator fault.

## HW_CI_SLEEP_SYSTICK
Ordinary Sleep/WFI interrupted by SysTick exception15 with external IRQs masked; interrupted frame follows WFI, delay and ADC state retained.

## HW_CI_SLEEP_TIM2
With SysTick disabled and only TIM2 enabled, exception44 interrupts WFI; ticks do not advance, restore IRQ controls and resume. Not Stop/current measurement.

## HW_CI_ADC_SERIES
Capture configured 2..20 contiguous published ADC samples; validate quality and ranges,
then retain raw measurements and mean/sample standard deviation (ddof=1) using runtime records.
A missing, stale or invalid sample prevents a successful summary. Not sensor calibration.

## HW_CI_RET_RECEIVER
The firmware calls app_step through app_receiver_step, so a forced return reaches a caller that
consumes it: app_received.produced holds the forced 42 and then the forced 0, while the caller's own
app_state copy (ticks 7 and 9) never appears. The call counter advances per accepted value. A refused
out-of-range value is not covered here; value encoding is checked by the V14 prototype. The scenario
depends on the caller storing the value, not on the debugger alone.

## HW_CI_MEASUREMENT_SERIES
Five publications are taken with execution continuing between samples, so the series varies in time:
board_adc_sequences increases without gaps and the values stay inside the plausible -40000..125000
mdegC domain with more than one distinct value. Records keep every sample. This checks the measurement
protocol on varying data, not sensor calibration, sample rate or accuracy.
