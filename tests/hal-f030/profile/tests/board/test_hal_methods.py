"""
RU: Проверки аргументов GPIO и управляемых ошибок RCC в HAL.
EN: HAL GPIO argument checks and controlled RCC error paths.
"""
from stm32_gdbtest import case


# Inspect HAL GPIO initialization arguments and the resulting pin configuration.
@case("HW_GPIO_ARGUMENTS", contracts=("gpio_arguments",), labels=("gpio", "contract"))
def gpio_arguments(t):
    # TECH-001/003: docs/ru/TESTING_TECHNIQUES.md (EN: docs/en/TESTING_TECHNIQUES.md).
    # The published call is the one for GPIOA, so the point carries that condition.
    t.reach("HAL_GPIO_Init", condition="GPIOx == GPIOA")

    # Check the published fields against the expected values.
    t.check([
        ("pin mask", "GPIO_Init->Pin", "GPIO_PIN_5"),
        ("output mode", "GPIO_Init->Mode", "GPIO_MODE_OUTPUT_PP"),
        ("no pull", "GPIO_Init->Pull", "GPIO_NOPULL"),
        ("low speed", "GPIO_Init->Speed", "GPIO_SPEED_FREQ_LOW")
    ])

    t.reach("platform_adc_start")

    # Verify PA5 output applied.
    t.check("PA5 output applied", t.read("GPIOA->MODER & GPIO_MODER_MODER5"), t.evaluate("GPIO_MODER_MODER5_0"))


# Select a GPIO toggle by its arguments and verify the output transition.
@case("HW_GPIO_FILTERED_CALL", contracts=("gpio_filtered_call",), labels=("gpio", "contract"))
def gpio_filtered_call(t):
    t.reach("HAL_GPIO_TogglePin",
            condition="GPIOx == GPIOA && GPIO_Pin == GPIO_PIN_5 && (GPIOA->ODR & GPIO_ODR_5) != 0")

    # Verify selected toggle starts High.
    t.check("selected toggle starts High", t.read("GPIOA->ODR & GPIO_ODR_5"))

    t.reach("platform_adc_start")

    # Verify selected toggle ends Low.
    t.check("selected toggle ends Low", t.read("GPIOA->ODR & GPIO_ODR_5"), 0)


# Force an RCC failure return and verify entry into the application error handler.
@case("HW_RCC_ERROR", contracts=("rcc_error",), labels=("rcc", "injection"))
def rcc_error(t):
    # TECH-004: synthetic return code, not an oscillator fault.
    t.reach("HAL_RCC_OscConfig")
    t.ret("HAL_ERROR")
    t.reach("Error_Handler")


# Inject a NULL oscillator configuration and verify the reviewed error path.
@case("HW_RCC_OSC_NULL", contracts=("rcc_osc_null",), labels=("rcc", "injection"))
def rcc_osc_null(t):
    # TECH-005: source-reviewed NULL guard, not arbitrary pointer corruption.
    t.reach("HAL_RCC_OscConfig")
    t.write("RCC_OscInitStruct", "0")

    # Verify NULL injected.
    t.check("NULL injected", t.read("RCC_OscInitStruct"), 0)

    t.reach("Error_Handler")


# Inject a NULL clock configuration and verify the reviewed error path.
@case("HW_RCC_CLOCK_NULL", contracts=("rcc_clock_null",), labels=("rcc", "injection"))
def rcc_clock_null(t):
    # TECH-005: source-reviewed NULL guard, not a physical clock failure.
    t.reach("HAL_RCC_ClockConfig")
    t.write("RCC_ClkInitStruct", "0")

    # Verify NULL injected.
    t.check("NULL injected", t.read("RCC_ClkInitStruct"), 0)

    t.reach("Error_Handler")
