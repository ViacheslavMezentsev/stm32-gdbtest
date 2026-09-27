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
    target.check("PC13 clock", target.value("(RCC->AHB1ENR & RCC_AHB1ENR_GPIOCEN) != 0"), 1)
    target.check("PC13 output", target.value("(GPIOC->MODER & GPIO_MODER_MODER13) == GPIO_MODER_MODER13_0"), 1)
