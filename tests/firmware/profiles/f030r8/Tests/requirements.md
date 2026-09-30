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
