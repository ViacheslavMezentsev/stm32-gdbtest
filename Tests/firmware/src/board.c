/* Board LED through CMSIS registers only; the family is selected by the device define. */
#include "app.h"

#if defined(STM32F030x8)
#include "stm32f0xx.h"
/* NUCLEO-F030R8: LD2 on PA5. */
void board_init(void)
{
    RCC->AHBENR |= RCC_AHBENR_GPIOAEN;
    (void)RCC->AHBENR;
    GPIOA->MODER = (GPIOA->MODER & ~GPIO_MODER_MODER5) | GPIO_MODER_MODER5_0;
}

void board_led_toggle(void)
{
    GPIOA->ODR ^= GPIO_ODR_5;
}
#elif defined(STM32F103xB)
#include "stm32f1xx.h"
/* BluePill: LED on PC13, push-pull output 2 MHz. */
void board_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_IOPCEN;
    (void)RCC->APB2ENR;
    GPIOC->CRH = (GPIOC->CRH & ~(GPIO_CRH_MODE13 | GPIO_CRH_CNF13)) | GPIO_CRH_MODE13_1;
}

void board_led_toggle(void)
{
    GPIOC->ODR ^= GPIO_ODR_ODR13;
}
#elif defined(STM32F411xE)
#include "stm32f4xx.h"
/* BlackPill F411: LED on PC13. */
void board_init(void)
{
    RCC->AHB1ENR |= RCC_AHB1ENR_GPIOCEN;
    (void)RCC->AHB1ENR;
    GPIOC->MODER = (GPIOC->MODER & ~GPIO_MODER_MODER13) | GPIO_MODER_MODER13_0;
}

void board_led_toggle(void)
{
    GPIOC->ODR ^= GPIO_ODR_OD13;
}
#else
#error "Unsupported CI device"
#endif
