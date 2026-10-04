# CI scenario requirements (f411ce)

## HW_CI_BOOT
At main, initialized delay is 500 ms and BSS counters are zero. After board initialization,
consecutive app_loop entries advance app_state.ticks by one.

## HW_CI_GPIO
At the first board_led_toggle, GPIOC clock is enabled; PC13 is a low-speed push-pull output,
initially High (LED off on WeAct BlackPill). This checks registers, not emitted light.

## HW_CI_CLOCK
HSI supplies nominal 16 MHz with AHB/APB1/APB2 divide-by-one. SystemCoreClock agrees;
SysTick uses core clock with LOAD=15999, enabled with IRQ. No frequency accuracy claim.

## HW_CI_BLINK
PC13 alternates across consecutive board_led_toggle entries, separated by at least
500 firmware milliseconds. Debugger stops are excluded from physical timing claims.

## HW_CI_TIM2_INIT
TIM2 uses internal 16 MHz clock, PSC=15999, ARR=99 (nominal 100 ms), upcounting, UIE/CEN.
NVIC IRQ28 is enabled and vector slot44 points to TIM2_IRQHandler.

## HW_CI_TIM2_IRQ
Natural TIM2 update enters exception44 with UIF set. Each handler publishes one event;
thread mode resumes. No EGR/software-pending injection is used; no jitter claim.

## HW_CI_SYSTICK_IRQ
Natural SysTick enters exception15 through vector15. The handler increments the
millisecond counter once, then thread mode can resume. No external time reference.

## HW_CI_ADC_INIT
ADC1 PCLK2/2=8 MHz, scan CH18/17 at480 cycles, TSVREFE without VBAT. DMA2 stream0/channel0 normal halfwords, IRQ56/vector72.

## HW_CI_ADC_DMA
Two natural scans complete two transfers each, exception72/TC without errors; raw values publish before sequence, stream stops and flags clear.

## HW_CI_ADC_UNITS
Factory provenance=2 using F411 3.3 V/30/110 C samples; plausible VDDA and temperature, not metrology.

## HW_CI_ADC_VECTORS
Five analytic anchors exercise two calibration points, midpoint, negative temperature and VDDA compensation.

## HW_CI_ADC_INVALID
Nineteen invalid inputs: zero/saturation/uint16 maximum in five arguments, equal/reversed calibration, invalid supply. Zero reading then normal recovery.

## HW_CI_ADC_TIMEOUT
Mask IRQ56: DMA completes without publication; error4 after at least20 firmware ticks.

## HW_CI_ADC_BUSY
Enable stream before sample: DMA ownership guard error6, no publication; no claim of active ADC conversion.

## HW_CI_ADC_DISABLED
Clear ADON before sample: error3, no publication. Not a forced HAL return code.

## HW_CI_RTC_INIT
LSI, calendar RTC PRER127/249, masked Alarm A, EXTI17 rising, IRQ41/vector57; no backup-domain reset.

## HW_CI_RTC_ALARM
Two natural alarms enter exception57 with ALRAF/EXTI17 pending; one publication per handler, thread resumes.

## HW_CI_RTC_DEADLINE
Inject zero mask in LSIRDY wait: error3 after at least1000 ticks, backup configuration retained, no application/event publication. Not a physical oscillator fault.

## HW_CI_SLEEP_SYSTICK
With both external NVIC banks masked, exception15 interrupts WFI; delay completes and ADC sequence retained. Restore IRQ controls.

## HW_CI_SLEEP_TIM2
Only IRQ28 enabled, SysTick stopped: exception44 interrupts WFI without tick advance; restore controls and resume. Not Stop or a power measurement.

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

## HW_CI_READ_WRITE
Reading `app_state` returns a mapping with the declared fields `led` and `ticks` as plain integers,
identical to a single-member read and to a field-set read. Writing 41 into the `uint32_t`
`app_state.ticks` reports the previous value, the applied value and a verified read-back, records the
mutation in the report, and the application continues from the written value (42 on the next loop
iteration). The scenario verifies typed reads of scalars and structs and one verified write; it does
not measure memory access speed, float formatting or writes to peripherals.
