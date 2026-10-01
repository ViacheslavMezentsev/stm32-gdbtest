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
