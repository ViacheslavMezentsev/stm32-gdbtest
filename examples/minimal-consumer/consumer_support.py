"""
RU: Выражения конфигурации GPIO для минимального примера.
EN: GPIO configuration expressions for the minimal consumer example.
"""
CLOCK_ENABLED = "(RCC->AHB1ENR & RCC_AHB1ENR_GPIOCEN) != 0"
