# CI scenario requirements (f411ce)

## HW_CI_BOOT
After reset the firmware reaches `app_loop`; `app_step` counts ticks in `app_state`.

## HW_CI_GPIO
At `board_led_toggle` the PC13 port clock is enabled and PC13 is configured as an output.
Register state only; LED light and blink rate are not measured.
