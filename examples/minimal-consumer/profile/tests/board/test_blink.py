from stm32_gdbtest import case
from consumer_support import CLOCK_ENABLED


@case("HW_CONSUMER_GPIO", labels=("gpio",), contracts=("consumer_gpio",))
def gpio(target):
    target.reach("app_loop")
    target.check("GPIOC clock", target.value(CLOCK_ENABLED), 1)
    target.check("PC13 output", target.value("(GPIOC->MODER & GPIO_MODER_MODER13) == GPIO_MODER_MODER13_0"), 1)
