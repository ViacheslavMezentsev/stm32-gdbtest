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
