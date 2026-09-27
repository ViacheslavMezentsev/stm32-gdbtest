from stm32_gdbtest import case


@case("HW_CI_BOOT", labels=("boot",), contracts=("ci_app_api",))
def boot(target):
    target.reach("app_loop")
    before = target.value("app_state.ticks")
    target.reach("app_loop")
    target.check("app_state.ticks advanced", target.value("app_state.ticks") - before, 1)


@case("HW_CI_GPIO", labels=("gpio",), contracts=("ci_gpio_macros",))
def gpio(target):
    # CMSIS macros are visible in board.c, the translation unit that includes the device header.
    target.reach("board_led_toggle")
    target.check("PB2 clock", target.value("(RCC->APB2ENR & RCC_APB2ENR_IOPBEN) != 0"), 1)
    target.check("PB2 output", target.value("(GPIOB->CRL & (GPIO_CRL_MODE2 | GPIO_CRL_CNF2)) == GPIO_CRL_MODE2_1"), 1)
