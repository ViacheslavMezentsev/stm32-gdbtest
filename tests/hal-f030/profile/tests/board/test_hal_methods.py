"""HAL-only techniques preserved from the F1/F4 consumer; reviewed for CubeF0."""
from stm32_gdbtest import case


@case("HW_GPIO_ARGUMENTS", contracts=("gpio_arguments",), labels=("gpio", "contract"))
def gpio_arguments(t):
    # TECH-001/003: docs/ru/TESTING_TECHNIQUES.md (EN: docs/en/TESTING_TECHNIQUES.md).
    t.reach("HAL_GPIO_Init", when="GPIOx == GPIOA")
    t.fields("*GPIO_Init", {"Pin": 1 << 5, "Mode": "GPIO_MODE_OUTPUT_PP",
                           "Pull": "GPIO_NOPULL", "Speed": "GPIO_SPEED_FREQ_LOW"})
    t.reach("platform_adc_start")
    t.check("PA5 output applied", t.value("(GPIOA->MODER >> 10) & 3"), 1)


@case("HW_GPIO_FILTERED_CALL", contracts=("gpio_filtered_call",), labels=("gpio", "contract"))
def gpio_filtered_call(t):
    t.reach("HAL_GPIO_TogglePin", when="GPIOx == GPIOA && GPIO_Pin == 32 && ((GPIOA->ODR >> 5) & 1) == 1")
    t.check("selected toggle starts High", t.value("(GPIOA->ODR >> 5) & 1"), 1)
    t.reach("platform_adc_start")
    t.check("selected toggle ends Low", t.value("(GPIOA->ODR >> 5) & 1"), 0)


@case("HW_RCC_ERROR", contracts=("rcc_error",), labels=("rcc", "injection"))
def rcc_error(t):
    # TECH-004: synthetic return code, not an oscillator fault.
    t.reach("HAL_RCC_OscConfig")
    t.force_return("(HAL_StatusTypeDef)1")
    t.reach("Error_Handler")


@case("HW_RCC_OSC_NULL", contracts=("rcc_osc_null",), labels=("rcc", "injection"))
def rcc_osc_null(t):
    # TECH-005: source-reviewed NULL guard, not arbitrary pointer corruption.
    t.reach("HAL_RCC_OscConfig")
    t.set_value("RCC_OscInitStruct", "0")
    t.check("NULL injected", t.value("RCC_OscInitStruct"), 0)
    t.reach("Error_Handler")


@case("HW_RCC_CLOCK_NULL", contracts=("rcc_clock_null",), labels=("rcc", "injection"))
def rcc_clock_null(t):
    # TECH-005: source-reviewed NULL guard, not a physical clock failure.
    t.reach("HAL_RCC_ClockConfig")
    t.set_value("RCC_ClkInitStruct", "0")
    t.check("NULL injected", t.value("RCC_ClkInitStruct"), 0)
    t.reach("Error_Handler")
