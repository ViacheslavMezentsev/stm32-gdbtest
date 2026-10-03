# CI scenario requirements (f030r8)

## HW_CI_BOOT
After reset Target reaches main with initialized app_delay=500 and zero BSS
app_state/board_ticks_ms. Firmware reaches app_loop and app_step increments the
iteration counter. HardFault is watched by the target profile.

## HW_CI_GPIO
Before the first board_led_toggle PA5 is an enabled output, push-pull, low speed,
no pull, initially Low (LD2 off). Register state is evidence, not optical measurement.

## HW_CI_CLOCK
HSI is ready and selected, AHB/APB dividers are one; SystemCoreClock reports the
nominal 8 MHz. SysTick LOAD=7999 and enabled core-clock interrupt establish a
nominal 1 ms tick. Reading CTRL clears COUNTFLAG; firmware does not use that flag.
This does not measure HSI accuracy or validate ADC/TIM3/RTC clocks.

## HW_CI_BLINK
At successive board_led_toggle entries PA5 is Low/High/Low with at least 500
board_ticks_ms between entries. The counter is driven by SysTick IRQ; unsigned
subtraction supports wraparound. Halt changes timing; no wall-clock or optical
accuracy claim. app_state.ticks counts iterations, not milliseconds.

## HW_CI_TIM3_INIT
TIM3 uses internal 8 MHz timer clock (APB /1), PSC=7999, ARR=99: nominal
100 ms update period. Upcounter and update IRQ enabled, NVIC IRQ16 enabled,
vector slot32 points to TIM3_IRQHandler. UG initialization event is discarded.

## HW_CI_TIM3_IRQ
Three natural TIM3 exception entries have IPSR=32 and UIF=1. Between entries
the handler publishes exactly one board_timer_events increment. Firmware then
reaches board_delay_ms in thread mode, rejecting an IRQ storm. No EGR or
NVIC injection. Halt may coalesce updates: no wall-clock period or lost-event
claim. HAL callback coverage is not preserved by this CMSIS scenario.

## HW_CI_ADC_INIT
HSI14 async ADC, calibrated/enabled, forward single 12-bit CH16/17 scan,
239.5-cycle sampling, internal paths enabled. DMA1 channel1 uses normal
halfword transfers, MINC, TC/TE interrupts and the SRAM buffer. IRQ9/vector25.
Calibration completion and configuration do not measure ADC accuracy.

## HW_CI_ADC_DMA
Two real scans finish DMA (CNDTR=0, TCIF, no TEIF); handler runs with IPSR25,
publishes both raw values before advancing sequence. No saturation or overrun.
No ADC DR read by tests, no injected conversion. No physical-unit claim yet.

## HW_CI_ADC_TIMEOUT
Disable DMA IRQ9 through logged NVIC mutation before acquisition. Hardware
finishes transfer, but no publication occurs; firmware reports error4 after
20 SysTick milliseconds and reaches board_adc_fault. Teardown resets the MCU.
This tests the CMSIS completion deadline, not HAL error-return injection.

## HW_CI_ADC_UNITS
Real DMA raw samples use F030 VREFINT_CAL/TS_CAL1 (30C/3.3V), typical negative
4.3mV/C slope. VDDA 2800..3600mV, die temperature -40..125C, quality3
(single-point + typical slope). This is plausibility, not accuracy validation.

## HW_CI_ADC_VECTORS
Seven fixed vectors run through the real firmware conversion by logged GDB
argument mutation: 30C anchor, supply compensation, +/-100 raw counts,
negative temperature and application VDDA endpoints 2400/3600mV.
Expected integer values use C truncation toward zero, not Python floor.

## HW_CI_ADC_INVALID
Each of the four inputs is tested at 0/4095/65535, then supply-out-of-window
inputs: result fields all zero. Normal acquisition afterwards restores
quality3; stale valid data must not survive an invalid conversion.

## HW_CI_SLEEP_SYSTICK
At the application's 500-tick delay, disable external IRQs, observe a SysTick
exception whose unwound interrupted PC follows WFI (0xBF30) in board_delay_ms.
SCR SLEEPDEEP/SLEEPONEXIT clear. Restore IRQs and reach the next app_loop with
at least 500 ticks elapsed and the ADC sequence retained. No residency claim.

## HW_CI_SLEEP_TIM3
At the 500-tick delay stop SysTick/clear its pending exception and leave only
TIM3 external IRQ. Observe TIM3 interrupting WFI with unchanged SysTick count.
Restore controls, complete the delay and retain ADC sequence. Eight bounded
attempts allow an IRQ preceding WFI; unwind failure is ERROR, no fallback PASS.
These tests do not prove current consumption, Stop mode or physical wake latency.

## HW_CI_RTC_INIT
RTC uses ready LSI, PRER=127/311 and 24-hour format. Alarm A masks all calendar
fields and subseconds, EXTI17 rising edge and NVIC IRQ2 enabled, vector18
points to RTC_IRQHandler. Initialization has completed with no error.
The fixture resets its calendar on boot, never asserts BDRST and refuses an
existing non-LSI RTC source. Nominal 40kHz LSI is not a precision timebase.

## HW_CI_RTC_ALARM
Two natural Alarm A entries have IPSR18, ALRAF and EXTI17 pending; the first
handler publishes one event before the next entry. Thread mode resumes after
the second event. No software IRQ or calendar injection, no accuracy or
backup retention claim. Debug halt can coalesce alarms.

## HW_CI_ADC_BUSY
Start continuous ADC conversions through logged MMIO writes before the first
board_adc_sample. Confirm ADSTART, then require error6 at board_adc_fault
with no published sequence or valid measurement. This exercises the actual
busy guard, not a HAL return injection. Teardown reset_run restores settings;
conversion overrun during this deliberately unconsumed stream is expected.

## HW_CI_RTC_DEADLINE
At rtc_wait(error3), set mask=0 to force the ready predicate false. Require
error3 at board_rtc_fault after at least 1000 SysTick ticks, unchanged BDCR,
zero app loops and alarm events. This checks the shared wait deadline and
error propagation, not physical LSI failure or every RTC initialization path.
Teardown reset_run restores execution; no backup-domain mutation is injected.

## HW_CI_ADC_SERIES
Capture configured 2..20 contiguous published ADC samples; validate quality and ranges,
then retain raw measurements and mean/sample standard deviation (ddof=1) using runtime records.
A missing, stale or invalid sample prevents a successful summary. Not sensor calibration.
