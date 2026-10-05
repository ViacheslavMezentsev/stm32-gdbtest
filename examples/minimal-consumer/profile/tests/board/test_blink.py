"""
RU: Минимальный пример проверки конфигурации GPIO потребителя.
EN: Minimal consumer example checking GPIO configuration.
"""
from stm32_gdbtest import case
from consumer_support import CLOCK_ENABLED


# Verify the board LED pin configuration and initial output state.
@case("HW_CONSUMER_GPIO", labels=("gpio",), contracts=("consumer_gpio",))
def gpio(t):
    t.reach("app_loop")

    # Check the GPIO clock, pin mode and initial output level.
    t.check("GPIOC clock", t.evaluate(CLOCK_ENABLED))
    t.check("PC13 output", t.evaluate("(GPIOC->MODER & GPIO_MODER_MODER13) == GPIO_MODER_MODER13_0"))
